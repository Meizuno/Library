from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from library.loan.domain import Loan


@pytest.fixture
def loaned_at() -> datetime:
    return datetime(2026, 5, 1, 10, 0, 0)


@pytest.fixture
def due_at(loaned_at: datetime) -> datetime:
    return loaned_at + timedelta(days=14)


@pytest.fixture
def valid_loan(loaned_at: datetime, due_at: datetime) -> Loan:
    return Loan(
        book_id=uuid4(),
        member_id=uuid4(),
        loaned_at=loaned_at,
        due_at=due_at,
    )


class TestLoanConstruction:
    def test_valid_loan(self, loaned_at: datetime, due_at: datetime):
        loan = Loan(
            book_id=uuid4(),
            member_id=uuid4(),
            loaned_at=loaned_at,
            due_at=due_at,
        )
        assert isinstance(loan.id, UUID)
        assert loan.returned_at is None
        assert not loan.is_returned

    def test_due_before_loaned_raises(self, loaned_at: datetime):
        with pytest.raises(ValueError):
            Loan(
                book_id=uuid4(),
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=loaned_at - timedelta(days=1),
            )

    def test_returned_before_loaned_raises(
        self, loaned_at: datetime, due_at: datetime
    ):
        with pytest.raises(ValueError):
            Loan(
                book_id=uuid4(),
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=due_at,
                returned_at=loaned_at - timedelta(hours=1),
            )

    def test_id_is_not_settable_via_constructor(
        self, loaned_at: datetime, due_at: datetime
    ):
        with pytest.raises(TypeError):
            Loan(  # pylint: disable=unexpected-keyword-arg
                id=uuid4(),
                book_id=uuid4(),
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=due_at,
            )


class TestLoanReturn:
    def test_mark_returned_sets_timestamp(
        self, valid_loan: Loan, due_at: datetime
    ):
        returned_at = due_at + timedelta(hours=1)
        valid_loan.mark_returned(returned_at)
        assert valid_loan.returned_at == returned_at
        assert valid_loan.is_returned

    def test_mark_returned_twice_raises(
        self, valid_loan: Loan, due_at: datetime
    ):
        valid_loan.mark_returned(due_at)
        with pytest.raises(ValueError):
            valid_loan.mark_returned(due_at + timedelta(hours=1))

    def test_mark_returned_before_loaned_raises(
        self, valid_loan: Loan, loaned_at: datetime
    ):
        with pytest.raises(ValueError):
            valid_loan.mark_returned(loaned_at - timedelta(hours=1))


class TestLoanOverdue:
    def test_not_overdue_when_now_before_due(
        self, valid_loan: Loan, loaned_at: datetime
    ):
        now = loaned_at + timedelta(days=1)
        assert valid_loan.is_overdue(now) is False

    def test_overdue_when_now_after_due_and_not_returned(
        self, valid_loan: Loan, due_at: datetime
    ):
        now = due_at + timedelta(hours=1)
        assert valid_loan.is_overdue(now) is True

    def test_not_overdue_when_returned(
        self, valid_loan: Loan, due_at: datetime
    ):
        valid_loan.mark_returned(due_at)
        now = due_at + timedelta(days=30)
        assert valid_loan.is_overdue(now) is False

    def test_not_overdue_at_exact_due_time(
        self, valid_loan: Loan, due_at: datetime
    ):
        assert valid_loan.is_overdue(due_at) is False


class TestLoanEquality:
    def test_equal_by_id(self, valid_loan: Loan):
        other = Loan(
            book_id=uuid4(),
            member_id=uuid4(),
            loaned_at=valid_loan.loaned_at,
            due_at=valid_loan.due_at,
        )
        other.id = valid_loan.id
        assert valid_loan == other

    def test_not_equal_if_different_id(self, valid_loan: Loan):
        other = Loan(
            book_id=valid_loan.book_id,
            member_id=valid_loan.member_id,
            loaned_at=valid_loan.loaned_at,
            due_at=valid_loan.due_at,
        )
        assert valid_loan != other

    def test_hashable_by_id(self, valid_loan: Loan):
        assert hash(valid_loan) == hash(valid_loan.id)
