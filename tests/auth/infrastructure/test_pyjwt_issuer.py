from uuid import uuid4

import pytest

from library.auth.domain import InvalidAccessToken
from library.auth.infrastructure import PyJWTTokenIssuer


# HS256 requires a key >= 32 bytes; PyJWT emits InsecureKeyLengthWarning
# below that. We use a 32+ byte test key throughout to keep pytest -W error clean.
_SECRET = "test-secret-key-must-be-at-least-32-bytes-long"
_OTHER_SECRET = "another-test-secret-key-with-32-plus-bytes-padding"


class TestPyJWTTokenIssuer:
    """Auth's TokenIssuer is now scoped to access + refresh tokens only.
    Verification tokens live in member.infrastructure.PyJWTVerificationTokenIssuer
    (see tests/member/infrastructure/test_pyjwt_verification_token_issuer.py)."""

    def test_round_trip_access_token(self):
        issuer = PyJWTTokenIssuer(secret_key=_SECRET)
        member_id = uuid4()
        token = issuer.issue_access_token(member_id)
        assert issuer.verify_access_token(token) == member_id

    def test_wrong_secret_rejects_token(self):
        a = PyJWTTokenIssuer(secret_key=_SECRET)
        b = PyJWTTokenIssuer(secret_key=_OTHER_SECRET)
        token = a.issue_access_token(uuid4())
        with pytest.raises(InvalidAccessToken):
            b.verify_access_token(token)

    def test_garbage_token_rejected(self):
        issuer = PyJWTTokenIssuer(secret_key=_SECRET)
        with pytest.raises(InvalidAccessToken):
            issuer.verify_access_token("not-a-jwt")

    def test_refresh_token_is_random(self):
        issuer = PyJWTTokenIssuer(secret_key=_SECRET)
        a = issuer.generate_refresh_token()
        b = issuer.generate_refresh_token()
        assert a != b
        assert len(a) > 32

    def test_refresh_token_hash_is_deterministic(self):
        issuer = PyJWTTokenIssuer(secret_key=_SECRET)
        token = "some-refresh-token"
        assert issuer.hash_refresh_token(token) == issuer.hash_refresh_token(
            token
        )

    def test_empty_secret_key_rejected(self):
        with pytest.raises(ValueError):
            PyJWTTokenIssuer(secret_key="")
