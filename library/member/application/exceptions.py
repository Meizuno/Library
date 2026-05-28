from library.shared.application.exceptions import ApplicationError


class MemberAlreadyExists(ApplicationError):
    pass


class MemberNotVerified(ApplicationError):
    """Raised when an action requires a verified member but the caller's
    Member has is_verified=False. The presentation layer maps this to a
    403 Forbidden."""
