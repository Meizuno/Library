# pylint: disable=wrong-import-position
# Env vars must be in place before any library import that may construct
# `Settings()` (which validates required fields at instantiation time).
import os

os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-must-be-at-least-32-bytes-long"
)
# DATABASE_URL / REDIS_URL are required by Settings() but tests override
# get_session / get_redis_client / get_cache, so the values are never used.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from library.auth.domain import (
    CredentialVerifier,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.auth.infrastructure import (
    InMemoryRefreshTokenRepository,
    PyJWTTokenIssuer,
)
from library.auth.presentation.api.dependencies import get_refresh_token_repo
from library.auth.presentation.api.security import (
    get_current_member,
    get_verified_member,
)
from library.book.domain import ISBN, Book, BookRepository
from library.book.infrastructure import InMemoryBookRepository
from library.book.presentation.api.dependencies import get_book_repo
from library.loan.domain import Loan, LoanRepository
from library.loan.infrastructure import InMemoryLoanRepository
from library.loan.presentation.api.dependencies import get_loan_repo
from library.member.domain import (
    Email,
    Member,
    MemberRepository,
    VerificationTokenIssuer,
)
from library.member.infrastructure import (
    InMemoryMemberRepository,
    MemberCredentialVerifier,
    PyJWTVerificationTokenIssuer,
)
from library.notification.domain import Notification, Notifier
from library.shared.application import Clock, PasswordHasher
from library.shared.presentation.api.dependencies import (
    get_clock,
    get_credential_verifier,
    get_member_repo,
    get_notifier,
    get_password_hasher,
    get_token_issuer,
    get_verification_token_issuer,
)
from library.shared.presentation.api.main import app


_TEST_SECRET = "test-secret-key-must-be-at-least-32-bytes-long"


class FakeClock:
    def __init__(self, fixed_now: datetime):
        self._now = fixed_now

    def now(self) -> datetime:
        return self._now


class FakePasswordHasher:
    """Reversible fake — fast, no real crypto. Tests pass plain-text 'password'
    and the resulting 'hashed:password' is what callers see as password_hash."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"hashed:{password}"


@dataclass
class _SentNotification:
    recipient: str
    notification: Notification


@dataclass
class FakeNotifier:
    """Records every `send` call. Tests assert against `.sent` to verify
    that notifications fire (or don't) without touching SMTP."""

    sent: list[_SentNotification] = field(default_factory=list)

    async def send(
        self, recipient: str, notification: Notification
    ) -> None:
        self.sent.append(
            _SentNotification(
                recipient=recipient, notification=notification
            )
        )


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
    # Default to verified=True so /loans tests (gated on is_verified)
    # work out of the box. Tests that want to exercise the unverified
    # path can build their own Member or call mark_unverified post-hoc.
    return Member(
        name="Name",
        email=valid_email,
        password_hash="hashed:password",
        is_verified=True,
    )


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
def password_hasher() -> PasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def token_issuer() -> TokenIssuer:
    return PyJWTTokenIssuer(
        secret_key=_TEST_SECRET,
        algorithm="HS256",
        access_token_ttl_minutes=15,
    )


@pytest.fixture
def verification_token_issuer() -> VerificationTokenIssuer:
    return PyJWTVerificationTokenIssuer(
        secret_key=_TEST_SECRET,
        algorithm="HS256",
        ttl_hours=24,
    )


@pytest.fixture
def refresh_token_repo() -> RefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


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
def notifier() -> Notifier:
    return FakeNotifier()


@pytest.fixture
def credential_verifier(
    member_repo: MemberRepository,
    password_hasher: PasswordHasher,
) -> CredentialVerifier:
    return MemberCredentialVerifier(member_repo, password_hasher)


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
    password_hasher: PasswordHasher,
    token_issuer: TokenIssuer,
    verification_token_issuer: VerificationTokenIssuer,
    credential_verifier: CredentialVerifier,
    refresh_token_repo: RefreshTokenRepository,
    notifier: Notifier,
    valid_member: Member,
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_book_repo] = lambda: book_repo
    app.dependency_overrides[get_member_repo] = lambda: member_repo
    app.dependency_overrides[get_loan_repo] = lambda: loan_repo
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[get_password_hasher] = lambda: password_hasher
    app.dependency_overrides[get_token_issuer] = lambda: token_issuer
    app.dependency_overrides[get_verification_token_issuer] = (
        lambda: verification_token_issuer
    )
    app.dependency_overrides[get_credential_verifier] = (
        lambda: credential_verifier
    )
    app.dependency_overrides[get_refresh_token_repo] = (
        lambda: refresh_token_repo
    )
    app.dependency_overrides[get_notifier] = lambda: notifier
    # Default: auth-gated tests assume an authenticated caller. Individual
    # tests can clear this override to exercise the 401 path.
    app.dependency_overrides[get_current_member] = lambda: valid_member
    app.dependency_overrides[get_verified_member] = lambda: valid_member
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()
