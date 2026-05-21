from library.domain import Loan, LoanRepository, LoanNotFound
from library.application import Clock
from library.application.commands import ReturnBookCommand


class ReturnBookUseCase:
    def __init__(self, loans: LoanRepository, clock: Clock):
        self._loans = loans
        self._clock = clock

    async def execute(self, command: ReturnBookCommand) -> Loan:
        loan = await self._loans.find_by_id(command.loan_id)
        if loan is None:
            raise LoanNotFound(f"Loan {command.loan_id} not found")

        loan.mark_returned(self._clock.now())
        await self._loans.save(loan)
        return loan
