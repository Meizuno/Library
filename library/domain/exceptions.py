class DomainError(Exception):
    pass


class BookNotFound(DomainError):
    pass


class BookNotAvailable(DomainError):
    pass


class MemberNotFound(DomainError):
    pass


class LoanNotFound(DomainError):
    pass


class InvalidLoanState(DomainError):
    pass
