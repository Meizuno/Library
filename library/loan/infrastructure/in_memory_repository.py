from uuid import UUID

from library.loan.domain import Loan, LoanNotFound


class InMemoryLoanRepository:
    def __init__(self):
        self._loan_db: dict[UUID, Loan] = {}

    async def create(self, loan: Loan) -> None:
        self._loan_db[loan.id] = loan

    async def update(self, loan: Loan) -> None:
        if loan.id not in self._loan_db:
            raise LoanNotFound(f"Loan {loan.id} not found")
        self._loan_db[loan.id] = loan

    async def find_by_id(self, loan_id: UUID) -> Loan | None:
        return self._loan_db.get(loan_id)

    async def find_active_by_book(self, book_id: UUID) -> Loan | None:
        for loan in self._loan_db.values():
            if loan.book_id == book_id and not loan.is_returned:
                return loan
        return None

    async def find_by_member(self, member_id: UUID) -> list[Loan]:
        return [
            loan
            for loan in self._loan_db.values()
            if loan.member_id == member_id
        ]

    async def list_all(self) -> list[Loan]:
        return list(self._loan_db.values())

    async def delete(self, loan_id: UUID) -> None:
        if loan_id not in self._loan_db:
            raise LoanNotFound(f"Loan {loan_id} not found")

        del self._loan_db[loan_id]
