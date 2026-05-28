from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

from library.book.domain import ISBN, Book, BookRepository
from library.book.infrastructure import InMemoryBookRepository
from library.book.presentation.api.dependencies import get_book_repo
from library.loan.domain import Loan, LoanRepository
from library.loan.infrastructure import InMemoryLoanRepository
from library.loan.presentation.api.dependencies import get_loan_repo
from library.member.domain import Email, Member, MemberRepository
from library.member.infrastructure import InMemoryMemberRepository
from library.member.presentation.api.dependencies import get_member_repo
from library.shared.application import Clock
from library.shared.presentation.api.dependencies import get_clock
from library.shared.presentation.api.main import app
from library.shared.presentation.cli.container import CliContext


class FakeClock:
    def __init__(self, fixed_now: datetime):
        self._now = fixed_now

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def valid_isbn() -> ISBN:
    return ISBN("978-3-16-148410-0")


@pytest.fixture
def valid_email() -> Email:
    return Email("user@example.com")


@pytest.fixture
def valid_book(valid_isbn: ISBN) -> Book:
    return Book(title="Title", author="Author", isbn=valid_isbn)


@pytest.fixture
def valid_member(valid_email: Email) -> Member:
    return Member(name="Name", email=valid_email)


@pytest.fixture
def valid_loan() -> Loan:
    loaned_at = datetime(2026, 5, 1, 10, 0, 0)
    return Loan(
        book_id=uuid4(),
        member_id=uuid4(),
        loaned_at=loaned_at,
        due_at=loaned_at + timedelta(days=14),
    )


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
    await book_repo.create(valid_book)
    return book_repo


@pytest.fixture
async def member_repo_with_member(
    member_repo: MemberRepository, valid_member: Member
) -> MemberRepository:
    await member_repo.create(valid_member)
    return member_repo


@pytest.fixture
async def client(
    book_repo: BookRepository,
    member_repo: MemberRepository,
    loan_repo: LoanRepository,
    clock: Clock,
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_book_repo] = lambda: book_repo
    app.dependency_overrides[get_member_repo] = lambda: member_repo
    app.dependency_overrides[get_loan_repo] = lambda: loan_repo
    app.dependency_overrides[get_clock] = lambda: clock
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_setup(monkeypatch) -> SimpleNamespace:
    """Replace `cli_context` in every command module with an in-memory one.

    Each test gets fresh in-memory repos that persist across multiple
    `runner.invoke` calls within the same test.
    """
    book_repo = InMemoryBookRepository()
    member_repo = InMemoryMemberRepository()
    loan_repo = InMemoryLoanRepository()
    clock = FakeClock(datetime(2026, 5, 20, 10, 0, 0))

    @asynccontextmanager
    async def fake_cli_context():
        yield CliContext(
            books=book_repo,
            members=member_repo,
            loans=loan_repo,
            clock=clock,
        )

    monkeypatch.setattr(
        "library.book.presentation.cli.commands.cli_context", fake_cli_context
    )
    monkeypatch.setattr(
        "library.member.presentation.cli.commands.cli_context", fake_cli_context
    )
    monkeypatch.setattr(
        "library.loan.presentation.cli.commands.cli_context", fake_cli_context
    )

    return SimpleNamespace(
        book_repo=book_repo,
        member_repo=member_repo,
        loan_repo=loan_repo,
        clock=clock,
    )
