from library.shared.application.exceptions import ApplicationError
from library.shared.domain.exceptions import DomainError


class BookNotFound(DomainError):
    pass


class BookNotAvailable(DomainError):
    pass


class BookAlreadyExists(ApplicationError):
    pass
