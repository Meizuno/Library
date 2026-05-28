from library.loan.application.commands import ReturnBookCommand
from library.loan.domain import Loan, LoanNotFound, LoanRepository
from library.shared.application import Clock


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
