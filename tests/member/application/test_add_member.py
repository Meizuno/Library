import pytest

from library.member.application import (
    AddMemberCommand,
    AddMemberUseCase,
    MemberAlreadyExists,
)
from library.member.domain import MemberRepository
from library.shared.application import PasswordHasher


class TestAddMemberUseCase:
    async def test_add_member_success(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher)
        member = await use_case.execute(member_command)
        assert member == await member_repo.find_by_id(member.id)
        # Password should be hashed (FakePasswordHasher prefixes with 'hashed:')
        assert member.password_hash == "hashed:password"

    async def test_add_member_duplicate(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher)
        await use_case.execute(member_command)

        with pytest.raises(MemberAlreadyExists):
            await use_case.execute(member_command)

    async def test_add_member_non_valid_name(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher)
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="", email="user@example.com", password="password"
                )
            )

    async def test_add_member_non_valid_email(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher)
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="not-an-email", password="password"
                )
            )

    async def test_add_member_short_password_raises(
        self,
        member_repo: MemberRepository,
        password_hasher: PasswordHasher,
    ):
        use_case = AddMemberUseCase(member_repo, password_hasher)
        with pytest.raises(ValueError, match="password must be at least"):
            await use_case.execute(
                AddMemberCommand(
                    name="Name", email="user@example.com", password="short"
                )
            )
