from uuid import uuid4

import pytest

from library.member.application import DeleteMemberUseCase
from library.member.domain import Member, MemberNotFound, MemberRepository


class TestDeleteMemberUseCase:
    async def test_delete_existing_member(
        self, member_repo_with_member: MemberRepository, valid_member: Member
    ):
        use_case = DeleteMemberUseCase(member_repo_with_member)
        await use_case.execute(valid_member.id)
        assert (
            await member_repo_with_member.find_by_id(valid_member.id) is None
        )

    async def test_delete_missing_member_raises(
        self, member_repo: MemberRepository
    ):
        use_case = DeleteMemberUseCase(member_repo)
        with pytest.raises(MemberNotFound):
            await use_case.execute(uuid4())
