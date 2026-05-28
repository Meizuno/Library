from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from library.member.domain import Member


class MemberResponse(BaseModel):
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


class MemberCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


class MemberVerifyRequest(BaseModel):
    token: str = Field(min_length=1)
