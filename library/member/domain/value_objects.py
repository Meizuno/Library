import re
from dataclasses import dataclass
from typing import ClassVar


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
