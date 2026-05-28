from library.shared.application.exceptions import ApplicationError


class InvalidCredentials(ApplicationError):
    """Raised when login is attempted with an unknown email or wrong password.

    Lives in the application layer because the credentials presented at the
    edge are an application-level concern — the domain doesn't know about
    cleartext passwords or email-format lookups."""
