import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from library.auth.domain import InvalidAccessToken


class PyJWTTokenIssuer:
    """Concrete `TokenIssuer` for the auth slice: issues + verifies access
    tokens (stateless JWTs) and generates + hashes refresh tokens (opaque
    random strings hashed with SHA-256 before storage).

    Verification tokens (e.g. for email confirmation) live in the member
    slice's `PyJWTVerificationTokenIssuer` — this issuer is purely an auth
    concern.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_ttl_minutes: int = 15,
    ):
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_token_ttl_minutes)

    def issue_access_token(self, member_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(member_id),
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidAccessToken(str(exc)) from exc

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidAccessToken("token missing sub claim")
        try:
            return UUID(sub)
        except ValueError as exc:
            raise InvalidAccessToken("sub claim is not a valid UUID") from exc

    def generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(64)

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
