from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from library.api import dependencies
from library.application.use_cases import (
    AddMemberUseCase,
    ReadMemberUseCase,
    ListMembersUseCase,
    DeleteMemberUseCase,
)
from library.api.schemas.member import MemberResponse, MemberCreate
from library.application import AddMemberCommand

router = APIRouter(prefix="/members", tags=["members"])


@router.get("")
async def list_members(
    list_members_use_case: ListMembersUseCase = Depends(
        dependencies.get_list_members_use_case
    ),
) -> list[MemberResponse]:
    members = await list_members_use_case.execute()
    return [MemberResponse.from_domain(member) for member in members]


@router.post("", status_code=201)
async def create_member(
    command: MemberCreate,
    add_member_use_case: AddMemberUseCase = Depends(
        dependencies.get_add_member_use_case
    ),
) -> MemberResponse:
    member = await add_member_use_case.execute(
        AddMemberCommand(name=command.name, email=command.email)
    )
    return MemberResponse.from_domain(member)


@router.get("/{member_id}")
async def read_member(
    member_id: UUID,
    read_member_use_case: ReadMemberUseCase = Depends(
        dependencies.get_read_member_use_case
    ),
) -> MemberResponse:
    member = await read_member_use_case.execute(member_id)
    if member is None:
        raise HTTPException(
            status_code=404, detail=f"Member {member_id} not found"
        )

    return MemberResponse.from_domain(member)


@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: UUID,
    delete_member_use_case: DeleteMemberUseCase = Depends(
        dependencies.get_delete_member_use_case
    ),
) -> None:
    await delete_member_use_case.execute(member_id)
