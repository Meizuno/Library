from library.shared.domain.exceptions import DomainError


class BookNotFound(DomainError):
    pass


class BookNotAvailable(DomainError):
    pass
