import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError(f"invalid email: {self.value!r}")

    def __str__(self) -> str:
        return self.value
