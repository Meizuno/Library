"""Base exception classes for the entire library.

Every module's exceptions.py inherits from one of these so the FastAPI
exception handlers in `library.shared.api.main` can map them to status
codes generically.

- DomainError: a domain invariant was broken (entity not found, business
  rule violated). Use in domain-level exceptions like BookNotFound.
- ApplicationError: a workflow / policy violation enforced by a use case
  or HTTP gate. Use in app-level exceptions like MemberAlreadyExists,
  InvalidCredentials, MemberNotVerified.
"""


class DomainError(Exception):
    pass


class ApplicationError(Exception):
    pass
