from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from library.cli.container import CliContext
from library.infrastructure import (
    InMemoryBookRepository,
    InMemoryMemberRepository,
    InMemoryLoanRepository,
)


class FakeClock:
    def __init__(self, fixed_now: datetime):
        self._now = fixed_now

    def now(self) -> datetime:
        return self._now


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
        "library.cli.commands.book.cli_context", fake_cli_context
    )
    monkeypatch.setattr(
        "library.cli.commands.member.cli_context", fake_cli_context
    )
    monkeypatch.setattr(
        "library.cli.commands.loan.cli_context", fake_cli_context
    )

    return SimpleNamespace(
        book_repo=book_repo,
        member_repo=member_repo,
        loan_repo=loan_repo,
        clock=clock,
    )
