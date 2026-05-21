from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from library.domain import Book, Member, Loan, ISBN, Email


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
