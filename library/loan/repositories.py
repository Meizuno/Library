from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Table,
    Uuid,
    delete,
    insert,
    select,
    update as sql_update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from library.loan.exceptions import LoanNotFound
from library.loan.models import Loan
from library.loan.ports import LoanRepository
from library.shared.infrastructure.sql_metadata import metadata

loans_table = Table(
    "loans",
    metadata,
    Column("id", Uuid, primary_key=True),
    # FK with ondelete="RESTRICT" prevents the database from removing
    # a referenced book or member while loans still point at it.
    # In normal app flow this never fires because books and members
    # are soft-deleted (their rows stay physically present); the FK
    # is the safety net for raw SQL, migrations, or buggy code paths
    # that bypass the soft-delete logic.
    Column(
        "book_id",
        Uuid,
        ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "member_id",
        Uuid,
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("loaned_at", DateTime, nullable=False),
    Column("due_at", DateTime, nullable=False),
    Column("returned_at", DateTime, nullable=True),
    Index("ix_loans_book_id", "book_id"),
    Index("ix_loans_member_id", "member_id"),
)


class SqlLoanRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_loan(self, row) -> Loan:
        loan = Loan(
            book_id=row.book_id,
            member_id=row.member_id,
            loaned_at=row.loaned_at,
            due_at=row.due_at,
            returned_at=row.returned_at,
        )
        loan.id = row.id
        return loan

    async def create(self, loan: Loan) -> None:
        stmt = insert(loans_table).values(
            id=loan.id,
            book_id=loan.book_id,
            member_id=loan.member_id,
            loaned_at=loan.loaned_at,
            due_at=loan.due_at,
            returned_at=loan.returned_at,
        )
        await self._session.execute(stmt)

    async def update(self, loan: Loan) -> None:
        stmt = (
            sql_update(loans_table)
            .where(loans_table.c.id == loan.id)
            .values(
                book_id=loan.book_id,
                member_id=loan.member_id,
                loaned_at=loan.loaned_at,
                due_at=loan.due_at,
                returned_at=loan.returned_at,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise LoanNotFound(f"Loan {loan.id} not found")

    async def find_by_id(self, loan_id: UUID) -> Loan | None:
        stmt = select(loans_table).where(loans_table.c.id == loan_id)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_loan(row) if row else None

    async def find_active_by_book(self, book_id: UUID) -> Loan | None:
        stmt = select(loans_table).where(
            loans_table.c.book_id == book_id,
            loans_table.c.returned_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_loan(row) if row else None

    async def find_by_member(self, member_id: UUID) -> list[Loan]:
        stmt = select(loans_table).where(
            loans_table.c.member_id == member_id
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_loan(row) for row in rows]

    async def list_all(self) -> list[Loan]:
        stmt = select(loans_table)
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_loan(row) for row in rows]

    async def delete(self, loan_id: UUID) -> None:
        stmt = delete(loans_table).where(loans_table.c.id == loan_id)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise LoanNotFound(f"Loan {loan_id} not found")


class LoanBookAvailability:
    """Implements `book.ports.BookAvailability` against the loan module.

    A book is available iff there is no active (not-yet-returned) Loan
    referencing it. The loan module owns this data (via
    `LoanRepository.find_active_by_book`); `book.api` consumes the
    boolean via the port.

    Asymmetric cross-module dependency by design — same shape as
    `MemberCredentialVerifier` implementing `auth.ports.CredentialVerifier`:
    the port lives in the consumer's ports.py, the impl lives where the
    data is. Structural typing matches the Protocol; the contract test
    in `tests/loan/repositories/test_book_availability.py` verifies it
    at runtime.
    """

    def __init__(self, loan_repo: LoanRepository):
        self._loan_repo = loan_repo

    async def is_available(self, book_id: UUID) -> bool:
        return await self._loan_repo.find_active_by_book(book_id) is None
