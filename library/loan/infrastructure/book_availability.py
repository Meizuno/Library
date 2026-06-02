from uuid import UUID

from library.loan.domain import LoanRepository


class LoanBookAvailability:
    """Implements `book.domain.BookAvailability` against the loan slice.

    A book is available iff there is no active (not-yet-returned) Loan
    referencing it. The loan slice owns this data (via `LoanRepository.
    find_active_by_book`); `book.presentation` consumes the boolean
    via the port.

    Asymmetric cross-slice dependency by design — same shape as
    `MemberCredentialVerifier` implementing `auth.domain.CredentialVerifier`:
    the port lives in the consumer slice's domain, the impl lives
    where the data is. Structural typing matches the Protocol; the
    contract test in `tests/loan/infrastructure/test_book_availability.py`
    verifies it at runtime.
    """

    def __init__(self, loan_repo: LoanRepository):
        self._loan_repo = loan_repo

    async def is_available(self, book_id: UUID) -> bool:
        return await self._loan_repo.find_active_by_book(book_id) is None
