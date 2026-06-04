from fastapi import APIRouter, Depends

from library.member.api.dependencies import get_list_members_use_case
from library.member.api.schemas import MemberResponse
from library.member.use_cases.list_members import ListMembersUseCase

router = APIRouter(prefix="/members", tags=["members"])


@router.get("")
async def list_members(
    list_members_use_case: ListMembersUseCase = Depends(
        get_list_members_use_case
    ),
) -> list[MemberResponse]:
    members = await list_members_use_case.execute()
    return [MemberResponse.from_domain(member) for member in members]
