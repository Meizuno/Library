from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from library.domain.value_objects import Email, ISBN


@dataclass(kw_only=True)
class Book:
    id: UUID = field(init=False, default_factory=uuid4)
    title: str
    author: str
    isbn: ISBN

    def __post_init__(self):
        self.title = self.title.strip()
        self.author = self.author.strip()

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


@dataclass(kw_only=True)
class Member:
    id: UUID = field(init=False, default_factory=uuid4)
    name: str
    email: Email

    def __post_init__(self):
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("name cannot be empty")

    def __eq__(self, other):
        if not isinstance(other, Member):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


@dataclass(kw_only=True)
class Loan:
    id: UUID = field(init=False, default_factory=uuid4)
    book_id: UUID
    member_id: UUID
    loaned_at: datetime
    due_at: datetime
    returned_at: datetime | None = None

    def __post_init__(self):
        if self.due_at < self.loaned_at:
            raise ValueError("due_at must be on or after loaned_at")
        if self.returned_at is not None and self.returned_at < self.loaned_at:
            raise ValueError("returned_at must be on or after loaned_at")

    def __eq__(self, other):
        if not isinstance(other, Loan):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def is_returned(self) -> bool:
        return self.returned_at is not None

    def is_overdue(self, now: datetime) -> bool:
        if self.is_returned:
            return False
        return now > self.due_at

    def mark_returned(self, at: datetime) -> None:
        if self.is_returned:
            raise ValueError("loan is already returned")
        if at < self.loaned_at:
            raise ValueError("return time must be on or after loaned_at")
        self.returned_at = at
