from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.auth.domain import InvalidAccessToken, TokenIssuer
from library.member.application import MemberNotVerified
from library.member.domain import Member, MemberRepository
from library.shared.presentation.api.dependencies import (
    get_member_repo,
    get_token_issuer,
)


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    issuer: TokenIssuer = Depends(get_token_issuer),
    members: MemberRepository = Depends(get_member_repo),
) -> Member:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        member_id = issuer.verify_access_token(credentials.credentials)
    except InvalidAccessToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    member = await members.find_by_id(member_id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Member no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return member


async def get_verified_member(
    member: Member = Depends(get_current_member),
) -> Member:
    """Variant of `get_current_member` that also requires the member to
    have verified their email. Used to gate endpoints that should only be
    callable by verified members (e.g. /loans/*).

    Returns the same Member instance; the verified-status check is the
    only added guarantee."""
    if not member.is_verified:
        raise MemberNotVerified(
            "Email verification required before this action."
        )
    return member
