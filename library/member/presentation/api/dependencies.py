from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.application import (
    AddMemberUseCase,
    DeleteMemberUseCase,
    ListMembersUseCase,
    ReadMemberUseCase,
)
from library.member.domain import MemberRepository
from library.member.infrastructure import (
    CachedMemberRepository,
    SqlMemberRepository,
)
from library.shared.application import PasswordHasher
from library.shared.infrastructure.cache import Cache
from library.shared.presentation.api.dependencies import (
    get_cache,
    get_password_hasher,
    get_session,
)


def get_member_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> MemberRepository:
    return CachedMemberRepository(SqlMemberRepository(session), cache)


def get_add_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> AddMemberUseCase:
    return AddMemberUseCase(member_repo, hasher)


def get_read_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> ReadMemberUseCase:
    return ReadMemberUseCase(member_repo)


def get_list_members_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> ListMembersUseCase:
    return ListMembersUseCase(member_repo)


def get_delete_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> DeleteMemberUseCase:
    return DeleteMemberUseCase(member_repo)
