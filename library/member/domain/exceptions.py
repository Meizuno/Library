from library.shared.domain.exceptions import DomainError


class MemberNotFound(DomainError):
    pass


class InvalidVerificationToken(DomainError):
    """Raised when an email-verification token is unrecognized, malformed,
    expired, or carries the wrong `purpose` claim."""
