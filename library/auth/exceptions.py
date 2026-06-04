from library.shared.exceptions import ApplicationError, DomainError


class InvalidAccessToken(DomainError):
    pass


class RefreshTokenInvalid(DomainError):
    pass


class RefreshTokenExpired(DomainError):
    pass


class RefreshTokenRevoked(DomainError):
    pass


class RefreshTokenNotFound(DomainError):
    pass


class InvalidCredentials(ApplicationError):
    """Raised when login is attempted with an unknown email or wrong password.

    Lives in the application-level taxonomy because the credentials presented
    at the edge are an application-level concern — the domain doesn't know
    about cleartext passwords or email-format lookups."""
