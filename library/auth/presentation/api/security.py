from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.auth.domain import InvalidAccessToken, TokenIssuer
from library.auth.presentation.api.dependencies import get_token_issuer
from library.member.domain import Member, MemberRepository
from library.member.presentation.api.dependencies import get_member_repo


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
