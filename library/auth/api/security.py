from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.auth.api.dependencies import get_token_issuer
from library.auth.exceptions import InvalidAccessToken
from library.auth.ports import TokenIssuer
from library.member.api.dependencies import get_member_repo
from library.member.exceptions import MemberNotVerified
from library.member.models import Member
from library.member.ports import MemberRepository

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
