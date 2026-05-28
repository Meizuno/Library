from uuid import UUID, uuid4
from dataclasses import dataclass, field

from library.member.domain.value_objects import Email


@dataclass(kw_only=True)
class Member:
    id: UUID = field(init=False, default_factory=uuid4)
    name: str
    email: Email
    password_hash: str
    is_verified: bool = False

    def __post_init__(self):
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.password_hash:
            raise ValueError("password_hash cannot be empty")

    def __eq__(self, other):
        if not isinstance(other, Member):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def mark_verified(self) -> None:
        """Flip is_verified to True. Idempotent — verifying an already-
        verified member is a no-op."""
        self.is_verified = True
