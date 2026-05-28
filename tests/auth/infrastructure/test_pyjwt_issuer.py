from uuid import uuid4

import pytest

from library.auth.domain import InvalidAccessToken
from library.auth.infrastructure import PyJWTTokenIssuer


class TestPyJWTTokenIssuer:
    def test_round_trip_access_token(self):
        issuer = PyJWTTokenIssuer(secret_key="s")
        member_id = uuid4()
        token = issuer.issue_access_token(member_id)
        assert issuer.verify_access_token(token) == member_id

    def test_wrong_secret_rejects_token(self):
        a = PyJWTTokenIssuer(secret_key="secret-a")
        b = PyJWTTokenIssuer(secret_key="secret-b")
        token = a.issue_access_token(uuid4())
        with pytest.raises(InvalidAccessToken):
            b.verify_access_token(token)

    def test_garbage_token_rejected(self):
        issuer = PyJWTTokenIssuer(secret_key="s")
        with pytest.raises(InvalidAccessToken):
            issuer.verify_access_token("not-a-jwt")

    def test_refresh_token_is_random(self):
        issuer = PyJWTTokenIssuer(secret_key="s")
        a = issuer.generate_refresh_token()
        b = issuer.generate_refresh_token()
        assert a != b
        assert len(a) > 32

    def test_refresh_token_hash_is_deterministic(self):
        issuer = PyJWTTokenIssuer(secret_key="s")
        token = "some-refresh-token"
        assert issuer.hash_refresh_token(token) == issuer.hash_refresh_token(
            token
        )

    def test_empty_secret_key_rejected(self):
        with pytest.raises(ValueError):
            PyJWTTokenIssuer(secret_key="")
