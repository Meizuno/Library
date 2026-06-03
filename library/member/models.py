import re
from dataclasses import dataclass, field
from typing import ClassVar
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError(f"invalid email: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Password:
    """A plain-text password, validated at construction time.

    Only used in transit (registration, login) — never persisted. Members
    store a `password_hash: str` produced by the PasswordHasher port.
    """

    MIN_LENGTH: ClassVar[int] = 8

    value: str

    def __post_init__(self):
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(
                f"password must be at least {self.MIN_LENGTH} characters"
            )

    def __str__(self) -> str:
        return "***"


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
