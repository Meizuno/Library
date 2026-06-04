from library.shared.exceptions import ApplicationError, DomainError


class MemberNotFound(DomainError):
    pass


class InvalidVerificationToken(DomainError):
    """Raised when an email-verification token is unrecognized, malformed,
    expired, or carries the wrong `purpose` claim."""


class MemberAlreadyExists(ApplicationError):
    pass


class MemberNotVerified(ApplicationError):
    """Raised when an action requires a verified member but the caller's
    Member has is_verified=False. The presentation layer maps this to a
    403 Forbidden."""
