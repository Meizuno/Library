from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from library.member.api.dependencies import get_verify_member_use_case
from library.member.api.schemas import MemberResponse
from library.member.use_cases.verify_member import (
    VerifyMemberCommand,
    VerifyMemberUseCase,
)


class MemberVerifyRequest(BaseModel):
    token: str = Field(min_length=1)


router = APIRouter(prefix="/members", tags=["members"])


@router.post("/verify")
async def verify_member(
    request: MemberVerifyRequest,
    verify_member_use_case: VerifyMemberUseCase = Depends(
        get_verify_member_use_case
    ),
) -> MemberResponse:
    member = await verify_member_use_case.execute(
        VerifyMemberCommand(token=request.token)
    )
    return MemberResponse.from_domain(member)
