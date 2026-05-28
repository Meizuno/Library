from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from library.member.domain import InvalidVerificationToken


_PURPOSE = "verify_email"


class PyJWTVerificationTokenIssuer:
    """Concrete `VerificationTokenIssuer` using PyJWT (HS256).

    Signs a `purpose=verify_email` claim alongside `sub`, `iat`, `exp`. The
    purpose check prevents an access token (which carries no purpose claim
    or a different one) from being substituted for a verification token.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        ttl_hours: int = 24,
    ):
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._ttl = timedelta(hours=ttl_hours)

    def issue(self, member_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(member_id),
            "purpose": _PURPOSE,
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidVerificationToken(str(exc)) from exc

        if payload.get("purpose") != _PURPOSE:
            raise InvalidVerificationToken(
                f"expected purpose {_PURPOSE!r}, got {payload.get('purpose')!r}"
            )

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidVerificationToken("token missing sub claim")
        try:
            return UUID(sub)
        except ValueError as exc:
            raise InvalidVerificationToken(
                "sub claim is not a valid UUID"
            ) from exc
