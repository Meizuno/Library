from dataclasses import dataclass


@dataclass(frozen=True)
class AddMemberCommand:
    name: str
    email: str
    password: str


@dataclass(frozen=True)
class VerifyMemberCommand:
    token: str
