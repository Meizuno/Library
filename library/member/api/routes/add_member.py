from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from library.member.api.dependencies import get_add_member_use_case
from library.member.api.schemas import MemberResponse
from library.member.use_cases.add_member import (
    AddMemberCommand,
    AddMemberUseCase,
)


class MemberCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


router = APIRouter(prefix="/members", tags=["members"])


@router.post("", status_code=201)
async def create_member(
    command: MemberCreate,
    add_member_use_case: AddMemberUseCase = Depends(get_add_member_use_case),
) -> MemberResponse:
    member = await add_member_use_case.execute(
        AddMemberCommand(
            name=command.name,
            email=command.email,
            password=command.password,
        )
    )
    return MemberResponse.from_domain(member)
