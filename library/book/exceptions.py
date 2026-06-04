from library.shared.exceptions import ApplicationError, DomainError


class BookNotFound(DomainError):
    pass


class BookNotAvailable(DomainError):
    pass


class BookAlreadyExists(ApplicationError):
    pass
