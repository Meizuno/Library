from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.ports import MemberRepository, VerificationTokenIssuer
from library.member.repositories import (
    CachedMemberRepository,
    PyJWTVerificationTokenIssuer,
    SqlMemberRepository,
)
from library.member.use_cases.add_member import AddMemberUseCase
from library.member.use_cases.delete_member import DeleteMemberUseCase
from library.member.use_cases.list_members import ListMembersUseCase
from library.member.use_cases.read_member import ReadMemberUseCase
from library.member.use_cases.verify_member import VerifyMemberUseCase
from library.shared.api.dependencies import (
    get_cache,
    get_event_publisher,
    get_password_hasher,
    get_session,
    get_settings,
)
from library.shared.config import Settings
from library.shared.ports import Cache, EventPublisher, PasswordHasher


def get_member_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> MemberRepository:
    return CachedMemberRepository(SqlMemberRepository(session), cache)


def get_verification_token_issuer(
    settings: Settings = Depends(get_settings),
) -> VerificationTokenIssuer:
    return PyJWTVerificationTokenIssuer(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        ttl_hours=settings.verification_token_ttl_hours,
    )


def get_add_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
    hasher: PasswordHasher = Depends(get_password_hasher),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> AddMemberUseCase:
    return AddMemberUseCase(member_repo, hasher, event_publisher)


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


def get_verify_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
    verification_tokens: VerificationTokenIssuer = Depends(
        get_verification_token_issuer
    ),
) -> VerifyMemberUseCase:
    return VerifyMemberUseCase(member_repo, verification_tokens)
