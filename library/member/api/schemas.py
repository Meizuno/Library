from uuid import UUID

from pydantic import BaseModel, EmailStr

from library.member.models import Member


class MemberResponse(BaseModel):
    """Response shape shared across all member routes (read, list, add,
    verify). Per-route request shapes (MemberCreate, MemberVerifyRequest)
    live with their route in api/routes/*.py.
    """

    id: UUID
    name: str
    email: EmailStr
    is_verified: bool

    @classmethod
    def from_domain(cls, member: Member) -> "MemberResponse":
        return cls(
            id=member.id,
            name=member.name,
            email=member.email.value,
            is_verified=member.is_verified,
        )
