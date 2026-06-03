from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from library.member.api.dependencies import get_read_member_use_case
from library.member.api.schemas import MemberResponse
from library.member.use_cases.read_member import ReadMemberUseCase

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/{member_id}")
async def read_member(
    member_id: UUID,
    read_member_use_case: ReadMemberUseCase = Depends(get_read_member_use_case),
) -> MemberResponse:
    member = await read_member_use_case.execute(member_id)
    if member is None:
        raise HTTPException(
            status_code=404, detail=f"Member {member_id} not found"
        )

    return MemberResponse.from_domain(member)
