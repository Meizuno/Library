from dataclasses import dataclass
from uuid import UUID

from library.loan.exceptions import LoanNotFound
from library.loan.models import Loan
from library.loan.ports import LoanRepository
from library.shared.ports import Clock


@dataclass(frozen=True)
class ReturnBookCommand:
    loan_id: UUID


class ReturnBookUseCase:
    def __init__(self, loans: LoanRepository, clock: Clock):
        self._loans = loans
        self._clock = clock

    async def execute(self, command: ReturnBookCommand) -> Loan:
        loan = await self._loans.find_by_id(command.loan_id)
        if loan is None:
            raise LoanNotFound(f"Loan {command.loan_id} not found")

        loan.mark_returned(self._clock.now())
        await self._loans.update(loan)
        return loan
