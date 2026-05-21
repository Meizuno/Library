from datetime import datetime

import pytest

from library.domain import (
    Book,
    Member,
    ISBN,
    Email,
    BookRepository,
    MemberRepository,
    LoanRepository,
)
from library.infrastructure import (
    InMemoryBookRepository,
    InMemoryMemberRepository,
    InMemoryLoanRepository,
)
from library.application import (
    AddBookCommand,
    AddMemberCommand,
    Clock,
)


class FakeClock:
    def __init__(self, fixed_now: datetime):
        self._now = fixed_now

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 20, 10, 0, 0)


@pytest.fixture
def clock(now: datetime) -> Clock:
    return FakeClock(now)


@pytest.fixture
def book_repo() -> BookRepository:
    return InMemoryBookRepository()


@pytest.fixture
def member_repo() -> MemberRepository:
    return InMemoryMemberRepository()


@pytest.fixture
def loan_repo() -> LoanRepository:
    return InMemoryLoanRepository()


@pytest.fixture
async def book_repo_with_book(
    book_repo: BookRepository, valid_book: Book
) -> BookRepository:
    await book_repo.save(valid_book)
    return book_repo


@pytest.fixture
async def member_repo_with_member(
    member_repo: MemberRepository, valid_member: Member
) -> MemberRepository:
    await member_repo.save(valid_member)
    return member_repo


@pytest.fixture
def book_command(valid_isbn: ISBN) -> AddBookCommand:
    return AddBookCommand(title="Title", author="Author", isbn=valid_isbn.value)


@pytest.fixture
def member_command(valid_email: Email) -> AddMemberCommand:
    return AddMemberCommand(name="Name", email=valid_email.value)
