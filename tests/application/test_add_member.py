import pytest

from library.domain import MemberRepository
from library.application.use_cases import AddMemberUseCase
from library.application import AddMemberCommand, MemberAlreadyExists


class TestAddMemberUseCase:
    async def test_add_member_success(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
    ):
        use_case = AddMemberUseCase(member_repo)
        member = await use_case.execute(member_command)
        assert member == await member_repo.find_by_id(member.id)

    async def test_add_member_duplicate(
        self,
        member_command: AddMemberCommand,
        member_repo: MemberRepository,
    ):
        use_case = AddMemberUseCase(member_repo)
        await use_case.execute(member_command)

        with pytest.raises(MemberAlreadyExists):
            await use_case.execute(member_command)

    async def test_add_member_non_valid_name(
        self, member_repo: MemberRepository
    ):
        use_case = AddMemberUseCase(member_repo)
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(name="", email="user@example.com")
            )

    async def test_add_member_non_valid_email(
        self, member_repo: MemberRepository
    ):
        use_case = AddMemberUseCase(member_repo)
        with pytest.raises(ValueError):
            await use_case.execute(
                AddMemberCommand(name="Name", email="not-an-email")
            )
