from fastapi import Depends

from library.member.application import (
    AddMemberUseCase,
    DeleteMemberUseCase,
    ListMembersUseCase,
    ReadMemberUseCase,
    VerifyMemberUseCase,
)
from library.member.domain import MemberRepository, VerificationTokenIssuer
from library.notification.domain import Notifier
from library.shared.application import PasswordHasher
from library.shared.config import Settings
from library.shared.presentation.api.dependencies import (
    get_member_repo,
    get_notifier,
    get_password_hasher,
    get_settings,
    get_verification_token_issuer,
)


def get_add_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
    hasher: PasswordHasher = Depends(get_password_hasher),
    notifier: Notifier = Depends(get_notifier),
    verification_tokens: VerificationTokenIssuer = Depends(
        get_verification_token_issuer
    ),
    settings: Settings = Depends(get_settings),
) -> AddMemberUseCase:
    return AddMemberUseCase(
        member_repo,
        hasher,
        notifier,
        verification_tokens,
        settings.app_base_url,
    )


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
