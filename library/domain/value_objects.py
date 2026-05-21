import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ISBN:
    """ISBN-10 або ISBN-13, з нормалізацією (видалення дефісів і пробілів)."""

    value: str

    def __post_init__(self):
        normalized = self.value.replace("-", "").replace(" ", "")
        if not re.fullmatch(r"\d{10}|\d{13}", normalized):
            raise ValueError(f"invalid ISBN: {self.value!r}")

        # frozen — обхід через __setattr__
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError(f"invalid email: {self.value!r}")

    def __str__(self) -> str:
        return self.value
