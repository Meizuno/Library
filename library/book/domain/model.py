from uuid import UUID, uuid4
from dataclasses import dataclass, field

from library.book.domain.value_objects import ISBN


@dataclass(kw_only=True)
class Book:
    id: UUID = field(init=False, default_factory=uuid4)
    title: str
    author: str
    isbn: ISBN
    description: str = ""

    def __post_init__(self):
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

    def __eq__(self, other):
        if not isinstance(other, Book):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
