from uuid import UUID

from fastapi import APIRouter, Depends

from library.member.api.dependencies import get_delete_member_use_case
from library.member.use_cases.delete_member import DeleteMemberUseCase

router = APIRouter(prefix="/members", tags=["members"])


@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: UUID,
    delete_member_use_case: DeleteMemberUseCase = Depends(
        get_delete_member_use_case
    ),
) -> None:
    await delete_member_use_case.execute(member_id)
