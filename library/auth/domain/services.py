from typing import Protocol
from uuid import UUID


class TokenIssuer(Protocol):
    """Port for issuing and verifying authentication tokens.

    Access tokens are short-lived stateless JWTs (encoded member_id + exp).
    Refresh tokens are opaque random strings; only their hash is stored.
    """

    def issue_access_token(self, member_id: UUID) -> str: ...
    def verify_access_token(self, token: str) -> UUID: ...
    def generate_refresh_token(self) -> str: ...
    def hash_refresh_token(self, token: str) -> str: ...
