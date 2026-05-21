from datetime import datetime
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport

from library.api.main import app
from library.api.dependencies import (
    get_book_repo,
    get_member_repo,
    get_loan_repo,
    get_clock,
)
from library.application import Clock
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
def book_repo() -> InMemoryBookRepository:
    return InMemoryBookRepository()


@pytest.fixture
def member_repo() -> InMemoryMemberRepository:
    return InMemoryMemberRepository()


@pytest.fixture
def loan_repo() -> InMemoryLoanRepository:
    return InMemoryLoanRepository()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 20, 10, 0, 0)


@pytest.fixture
def clock(now: datetime) -> Clock:
    return FakeClock(now)


@pytest.fixture
async def client(
    book_repo: InMemoryBookRepository,
    member_repo: InMemoryMemberRepository,
    loan_repo: InMemoryLoanRepository,
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
