from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from library.loan.domain import Loan, LoanNotFound, LoanRepository
from library.loan.infrastructure import InMemoryLoanRepository, SqlLoanRepository


class TestProtocolSatisfaction:
    def test_in_memory_loan_repo_satisfies_protocol(self):
        repo: LoanRepository = InMemoryLoanRepository()
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_active_by_book")
        assert hasattr(repo, "find_by_member")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_loan_repo_satisfies_protocol(self):
        repo: LoanRepository = SqlLoanRepository(AsyncSession())
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_active_by_book")
        assert hasattr(repo, "find_by_member")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")


class TestLoanRepository:
    async def test_get_list_without_loan(self, empty_loan_repo: LoanRepository):
        assert await empty_loan_repo.list_all() == []

    async def test_create_loan(
        self, empty_loan_repo: LoanRepository, valid_loan: Loan
    ):
        await empty_loan_repo.create(valid_loan)
        assert await empty_loan_repo.find_by_id(valid_loan.id) == valid_loan

    async def test_read_unsaved_loan(self, empty_loan_repo: LoanRepository):
        assert await empty_loan_repo.find_by_id(uuid4()) is None

    async def test_get_list_saved_loan(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        assert await loan_repo_with_loan.list_all() == [valid_loan]

    async def test_get_immutable_list_saved_loan(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        loan_list = await loan_repo_with_loan.list_all()
        loan_list.append(valid_loan)
        assert await loan_repo_with_loan.list_all() == [valid_loan]

    async def test_update_saved_loan(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        valid_loan.mark_returned(valid_loan.due_at)
        await loan_repo_with_loan.update(valid_loan)
        saved_loan = await loan_repo_with_loan.find_by_id(valid_loan.id)
        assert saved_loan.is_returned

    async def test_update_unsaved_loan_raises(
        self, empty_loan_repo: LoanRepository, valid_loan: Loan
    ):
        with pytest.raises(LoanNotFound):
            await empty_loan_repo.update(valid_loan)

    async def test_delete_saved_loan(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        assert await loan_repo_with_loan.delete(valid_loan.id) is None
        assert await loan_repo_with_loan.list_all() == []

    async def test_delete_unsaved_loan(self, empty_loan_repo: LoanRepository):
        with pytest.raises(LoanNotFound):
            await empty_loan_repo.delete(uuid4())

    async def test_find_active_by_book_returns_active_loan(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        found = await loan_repo_with_loan.find_active_by_book(
            valid_loan.book_id
        )
        assert found == valid_loan

    async def test_find_active_by_book_skips_returned(
        self, loan_repo_with_loan: LoanRepository, valid_loan: Loan
    ):
        valid_loan.mark_returned(valid_loan.due_at)
        await loan_repo_with_loan.update(valid_loan)
        found = await loan_repo_with_loan.find_active_by_book(
            valid_loan.book_id
        )
        assert found is None

    async def test_find_active_by_book_returns_none_when_no_loan(
        self, empty_loan_repo: LoanRepository
    ):
        assert await empty_loan_repo.find_active_by_book(uuid4()) is None

    async def test_find_by_member_returns_loans(
        self, empty_loan_repo: LoanRepository
    ):
        member_id = uuid4()
        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        loan_1 = Loan(
            book_id=uuid4(),
            member_id=member_id,
            loaned_at=loaned_at,
            due_at=loaned_at + timedelta(days=14),
        )
        loan_2 = Loan(
            book_id=uuid4(),
            member_id=member_id,
            loaned_at=loaned_at,
            due_at=loaned_at + timedelta(days=14),
        )
        await empty_loan_repo.create(loan_1)
        await empty_loan_repo.create(loan_2)

        loans = await empty_loan_repo.find_by_member(member_id)
        assert set(loans) == {loan_1, loan_2}

    async def test_find_by_member_returns_empty_when_no_loans(
        self, empty_loan_repo: LoanRepository
    ):
        assert await empty_loan_repo.find_by_member(uuid4()) == []
