from typing import Protocol
from uuid import UUID


class BookAvailability(Protocol):
    """Port for checking whether a book is currently available to borrow.

    A book is **available** when no active (not-yet-returned) Loan
    references it. The truth lives in the loan slice — this port lets
    book.presentation expose availability on BookResponse without
    book/ importing from loan/ (which would invert the established
    dependency direction).

    The impl will live in `loan/infrastructure/` (loan owns the data).
    Composition root wires them — same asymmetric pattern as
    `auth.domain.CredentialVerifier`.
    """

    async def is_available(self, book_id: UUID) -> bool: ...
