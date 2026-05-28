from library.shared.application.exceptions import ApplicationError
from library.shared.domain.exceptions import DomainError


class InvalidCredentials(ApplicationError):
    pass


class InvalidAccessToken(DomainError):
    pass


class RefreshTokenInvalid(DomainError):
    pass


class RefreshTokenExpired(DomainError):
    pass


class RefreshTokenRevoked(DomainError):
    pass
