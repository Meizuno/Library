import pytest

from library.member.application import (
    AddMemberCommand,
    AddMemberUseCase,
    MemberAlreadyExists,
)
from library.member.domain import MemberRepository, VerificationTokenIssuer
from library.shared.application import PasswordHasher

from tests.conftest import FakeNotifier


_APP_BASE_URL = "http://localhost:8000"


def _make_use_case(
    member_repo: MemberRepository,
    password_hasher: PasswordHasher,
    notifier: FakeNotifier,
    verification_token_issuer: VerificationTokenIssuer,
) -> AddMemberUseCase:
    return AddMemberUseCase(
        member_repo,
        password_hasher,
        notifier,
        verification_token_issuer,
        _APP_BASE_URL,
    )


class TestAddMemberUseCase:
    async def test_add_member_success(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        member = await use_case.execute(member_command)
        assert member == await member_repo.find_by_id(member.id)
        # Password should be hashed (FakePasswordHasher prefixes with 'hashed:')
        assert member.password_hash == "hashed:password"
        # New members are not yet verified.
        assert member.is_verified is False

    async def test_add_member_welcome_email_contains_verification_link(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        member = await use_case.execute(member_command)

        assert len(notifier.sent) == 1
        welcome = notifier.sent[0]
        assert welcome.recipient == member.email.value
        assert "Welcome" in welcome.notification.subject
        assert member.name in welcome.notification.body

        # The body contains a clickable verification URL of the form
        # `{app_base_url}/members/verify?token=<JWT>`. Extract it and
        # confirm the token decodes back to this member's id.
        body = welcome.notification.body
        urls = [
            word
            for word in body.split()
            if word.startswith(f"{_APP_BASE_URL}/members/verify?token=")
        ]
        assert len(urls) == 1
        token = urls[0].split("token=", 1)[1]
        assert verification_token_issuer.verify(token) == member.id

    async def test_add_member_duplicate_does_not_send_extra_email(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        await use_case.execute(member_command)

        with pytest.raises(MemberAlreadyExists):
            await use_case.execute(member_command)

        # Only the first (successful) registration sent an email.
        assert len(notifier.sent) == 1

    async def test_add_member_non_valid_name(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="", email="user@example.com", password="password"
                )
            )
        assert notifier.sent == []

    async def test_add_member_non_valid_email(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="not-an-email", password="password"
                )
            )
        assert notifier.sent == []

    async def test_add_member_short_password_raises(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, notifier, verification_token_issuer
        )
        with pytest.raises(ValueError, match="password must be at least"):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="user@example.com", password="short"
                )
            )
        assert notifier.sent == []
