from uuid import UUID

from sqlalchemy import delete, insert, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from library.loan.domain import Loan, LoanNotFound
from library.loan.infrastructure.sql_table import loans_table


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
