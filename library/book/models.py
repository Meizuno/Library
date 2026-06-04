import re
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ISBN:
    """ISBN-10 або ISBN-13, з нормалізацією (видалення дефісів і пробілів)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.replace("-", "").replace(" ", "")
        if not re.fullmatch(r"\d{10}|\d{13}", normalized):
            raise ValueError(f"invalid ISBN: {self.value!r}")

        # frozen — обхід через __setattr__
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(kw_only=True)
class Book:
    id: UUID = field(init=False, default_factory=uuid4)
    title: str
    author: str
    isbn: ISBN
    description: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Normalize and validate invariants. Safe to call after mutation."""
        self.title = self.title.strip()
        self.author = self.author.strip()
        self.description = self.description.strip()

        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.author:
            raise ValueError("author cannot be empty")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Book):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
