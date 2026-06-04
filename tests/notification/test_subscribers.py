from uuid import uuid4

from library.member.events import MemberRegistered
from library.member.ports import VerificationTokenIssuer
from library.notification.subscribers import (
    SendVerificationEmailOnRegistration,
)
from tests.conftest import FakeNotifier

_APP_BASE_URL = "http://localhost:8000"


class TestSendVerificationEmailOnRegistration:
    async def test_sends_email_to_member(
        self, verification_token_issuer: VerificationTokenIssuer
    ):
        notifier = FakeNotifier()
        subscriber = SendVerificationEmailOnRegistration(
            notifier=notifier,
            verification_tokens=verification_token_issuer,
            app_base_url=_APP_BASE_URL,
        )
        event = MemberRegistered(
            member_id=uuid4(), name="Name", email="user@example.com"
        )

        await subscriber(event)

        assert len(notifier.sent) == 1
        sent = notifier.sent[0]
        assert sent.recipient == "user@example.com"
        assert "Welcome" in sent.notification.subject
        assert "Name" in sent.notification.body

    async def test_body_contains_verification_link_with_valid_token(
        self, verification_token_issuer: VerificationTokenIssuer
    ):
        notifier = FakeNotifier()
        subscriber = SendVerificationEmailOnRegistration(
            notifier=notifier,
            verification_tokens=verification_token_issuer,
            app_base_url=_APP_BASE_URL,
        )
        member_id = uuid4()
        event = MemberRegistered(
            member_id=member_id, name="Name", email="user@example.com"
        )

        await subscriber(event)

        body = notifier.sent[0].notification.body
        # The body contains a clickable verification URL of the form
        # `{app_base_url}/members/verify?token=<JWT>`. Extract and
        # confirm the token decodes back to this member's id.
        urls = [
            word
            for word in body.split()
            if word.startswith(f"{_APP_BASE_URL}/members/verify?token=")
        ]
        assert len(urls) == 1
        token = urls[0].split("token=", 1)[1]
        assert verification_token_issuer.verify(token) == member_id

    async def test_trailing_slash_on_base_url_does_not_double_slash(
        self, verification_token_issuer: VerificationTokenIssuer
    ):
        notifier = FakeNotifier()
        subscriber = SendVerificationEmailOnRegistration(
            notifier=notifier,
            verification_tokens=verification_token_issuer,
            app_base_url="http://localhost:8000/",
        )
        event = MemberRegistered(
            member_id=uuid4(), name="Name", email="user@example.com"
        )

        await subscriber(event)

        body = notifier.sent[0].notification.body
        assert "http://localhost:8000/members/verify?token=" in body
        assert "//members" not in body
