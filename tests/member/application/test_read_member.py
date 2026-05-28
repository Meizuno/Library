from uuid import uuid4

from library.member.application import ReadMemberUseCase
from library.member.domain import Member, MemberRepository


class TestReadMemberUseCase:
    async def test_read_existing_member(
        self, member_repo_with_member: MemberRepository, valid_member: Member
    ):
        use_case = ReadMemberUseCase(member_repo_with_member)
        assert await use_case.execute(valid_member.id) == valid_member

    async def test_read_missing_member_returns_none(
        self, member_repo: MemberRepository
    ):
        use_case = ReadMemberUseCase(member_repo)
        assert await use_case.execute(uuid4()) is None
