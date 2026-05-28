import pytest

from library.member.application import (
    AddMemberCommand,
    AddMemberUseCase,
    MemberAlreadyExists,
)
from library.member.domain import MemberRepository
from library.shared.application import PasswordHasher

from tests.conftest import FakeNotifier


class TestAddMemberUseCase:
    async def test_add_member_success(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
        member = await use_case.execute(member_command)
        assert member == await member_repo.find_by_id(member.id)
        # Password should be hashed (FakePasswordHasher prefixes with 'hashed:')
        assert member.password_hash == "hashed:password"

    async def test_add_member_sends_welcome_email(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
        member = await use_case.execute(member_command)

        assert len(notifier.sent) == 1
        welcome = notifier.sent[0]
        assert welcome.recipient == member.email.value
        assert "Welcome" in welcome.notification.subject
        assert member.name in welcome.notification.body

    async def test_add_member_duplicate_does_not_send_extra_email(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
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
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="", email="user@example.com", password="password"
                )
            )
        # Failed validation must not send a welcome email.
        assert notifier.sent == []

    async def test_add_member_non_valid_email(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        notifier: FakeNotifier,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
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
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher, notifier)
        with pytest.raises(ValueError, match="password must be at least"):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="user@example.com", password="short"
                )
            )
        assert notifier.sent == []
