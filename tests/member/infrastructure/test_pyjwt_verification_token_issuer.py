from uuid import uuid4

import pytest

from library.auth.infrastructure import PyJWTTokenIssuer
from library.member.domain import InvalidVerificationToken
from library.member.infrastructure import PyJWTVerificationTokenIssuer


_SECRET = "test-secret-key-must-be-at-least-32-bytes-long"
_OTHER_SECRET = "another-test-secret-key-with-32-plus-bytes-padding"


class TestPyJWTVerificationTokenIssuer:
    def test_round_trip(self):
        issuer = PyJWTVerificationTokenIssuer(secret_key=_SECRET)
        member_id = uuid4()
        token = issuer.issue(member_id)
        assert issuer.verify(token) == member_id

    def test_wrong_secret_rejects_token(self):
        a = PyJWTVerificationTokenIssuer(secret_key=_SECRET)
        b = PyJWTVerificationTokenIssuer(secret_key=_OTHER_SECRET)
        token = a.issue(uuid4())
        with pytest.raises(InvalidVerificationToken):
            b.verify(token)

    def test_garbage_token_rejected(self):
        issuer = PyJWTVerificationTokenIssuer(secret_key=_SECRET)
        with pytest.raises(InvalidVerificationToken):
            issuer.verify("not-a-jwt")

    def test_access_token_rejected_as_verification_token(self):
        # An access token (no purpose claim) signed with the same secret
        # must not be accepted by the verification-token verifier.
        access_issuer = PyJWTTokenIssuer(secret_key=_SECRET)
        verify_issuer = PyJWTVerificationTokenIssuer(secret_key=_SECRET)
        access_token = access_issuer.issue_access_token(uuid4())
        with pytest.raises(InvalidVerificationToken):
            verify_issuer.verify(access_token)

    def test_empty_secret_key_rejected(self):
        with pytest.raises(ValueError):
            PyJWTVerificationTokenIssuer(secret_key="")
