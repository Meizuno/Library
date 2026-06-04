from dataclasses import dataclass, field

import pytest

from library.member.events import MemberRegistered
from library.member.exceptions import MemberAlreadyExists
from library.member.ports import MemberRepository
from library.member.use_cases.add_member import (
    AddMemberCommand,
    AddMemberUseCase,
)
from library.shared.ports import PasswordHasher


@dataclass
class FakeEventPublisher:
    """Records every published event. Tests assert against `.published`
    to verify the use case emitted the expected event(s) without wiring
    up real subscribers."""

    published: list[object] = field(default_factory=list)

    async def publish(self, event: object) -> None:
        self.published.append(event)


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


def _make_use_case(
    member_repo: MemberRepository,
    password_hasher: PasswordHasher,
    event_publisher: FakeEventPublisher,
) -> AddMemberUseCase:
    return AddMemberUseCase(member_repo, password_hasher, event_publisher)


class TestAddMemberUseCase:
    async def test_add_member_success(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        member = await use_case.execute(member_command)
        assert member == await member_repo.find_by_id(member.id)
        # Password should be hashed (FakePasswordHasher prefixes with 'hashed:')
        assert member.password_hash == "hashed:password"
        # New members are not yet verified.
        assert member.is_verified is False

    async def test_publishes_member_registered_with_correct_payload(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        # The use case knows nothing about email — it just emits the
        # fact of registration. The notification subscriber (covered in
        # tests/notification/test_subscribers.py) turns the fact into
        # an email; this test only asserts the publishing side.
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        member = await use_case.execute(member_command)

        assert event_publisher.published == [
            MemberRegistered(
                member_id=member.id,
                name=member.name,
                email=member.email.value,
            )
        ]

    async def test_add_member_duplicate_does_not_publish_extra_event(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        await use_case.execute(member_command)

        with pytest.raises(MemberAlreadyExists):
            await use_case.execute(member_command)

        # Only the first (successful) registration emitted an event.
        assert len(event_publisher.published) == 1

    async def test_add_member_non_valid_name(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="", email="user@example.com", password="password"
                )
            )
        assert event_publisher.published == []

    async def test_add_member_non_valid_email(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="not-an-email", password="password"
                )
            )
        assert event_publisher.published == []

    async def test_add_member_short_password_raises(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
        event_publisher: FakeEventPublisher,
    ):
        use_case = _make_use_case(
            member_repo, password_hasher, event_publisher
        )
        with pytest.raises(ValueError, match="password must be at least"):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="user@example.com", password="short"
                )
            )
        assert event_publisher.published == []
