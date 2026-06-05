from typing import cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.ports import MemberRepository, VerificationTokenIssuer
from library.member.repositories import (
    CachedMemberRepository,
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
)
from library.shared.ports import Cache, EventPublisher, PasswordHasher


def get_member_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> MemberRepository:
    return CachedMemberRepository(SqlMemberRepository(session), cache)


def get_verification_token_issuer(
    request: Request,
) -> VerificationTokenIssuer:
    """Resolve the application-scoped verification-token issuer stashed
    on `app.state` during lifespan startup. Same instance is bound to
    the MemberRegistered subscriber, so the verify flow and the
    welcome-email link agree on JWT config without a second
    construction site.
    """
    return cast(
        VerificationTokenIssuer, request.app.state.verification_tokens
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
