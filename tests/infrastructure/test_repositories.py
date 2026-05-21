from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fakeredis import FakeAsyncRedis

from library.domain import (
    Book,
    Member,
    Loan,
    ISBN,
    Email,
    BookRepository,
    MemberRepository,
    LoanRepository,
    BookNotFound,
    MemberNotFound,
    LoanNotFound,
)
from library.infrastructure import (
    InMemoryBookRepository,
    InMemoryMemberRepository,
    InMemoryLoanRepository,
    CachedBookRepository,
    CachedMemberRepository,
    RedisCache,
)
from library.infrastructure.sql import (
    SqlBookRepository,
    SqlMemberRepository,
    SqlLoanRepository,
)


class TestProtocolSatisfaction:
    def test_in_memory_book_repo_satisfies_protocol(self):
        repo: BookRepository = InMemoryBookRepository()
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_in_memory_member_repo_satisfies_protocol(self):
        repo: MemberRepository = InMemoryMemberRepository()
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_cached_book_repo_satisfies_protocol(self, sql_book_repo):
        repo: BookRepository = CachedBookRepository(
            sql_book_repo, RedisCache(FakeAsyncRedis(), 300)
        )
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_cached_member_repo_satisfies_protocol(self, sql_member_repo):
        repo: MemberRepository = CachedMemberRepository(
            sql_member_repo, RedisCache(FakeAsyncRedis(), 300)
        )
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_book_repo_satisfies_protocol(self):
        repo: BookRepository = SqlBookRepository(AsyncSession())
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_member_repo_satisfies_protocol(self):
        repo: MemberRepository = SqlMemberRepository(AsyncSession())
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_in_memory_loan_repo_satisfies_protocol(self):
        repo: LoanRepository = InMemoryLoanRepository()
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_active_by_book")
        assert hasattr(repo, "find_by_member")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_loan_repo_satisfies_protocol(self):
        repo: LoanRepository = SqlLoanRepository(AsyncSession())
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_active_by_book")
        assert hasattr(repo, "find_by_member")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")


class TestBookRepository:
    async def test_get_list_without_book(self, empty_book_repo: BookRepository):
        assert await empty_book_repo.list_all() == []

    async def test_save_book(
        self, empty_book_repo: BookRepository, valid_book: Book
    ):
        await empty_book_repo.save(valid_book)
        await empty_book_repo.list_all()
        assert await empty_book_repo.find_by_id(valid_book.id) == valid_book

    async def test_read_unsaved_book(self, empty_book_repo: BookRepository):
        assert await empty_book_repo.find_by_id(uuid4()) is None

    async def test_read_book_by_isbn(
        self,
        book_repo_with_book: BookRepository,
        valid_book: Book,
        valid_isbn: ISBN,
    ):
        assert await book_repo_with_book.find_by_isbn(valid_isbn) == valid_book

    async def test_get_list_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        assert await book_repo_with_book.list_all() == [valid_book]

    async def test_get_immutable_list_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        book_list = await book_repo_with_book.list_all()
        book_list.append(valid_book)
        assert await book_repo_with_book.list_all() == [valid_book]

    async def test_update_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        valid_book.title = "Updated title"
        await book_repo_with_book.save(valid_book)
        saved_book = await book_repo_with_book.find_by_id(valid_book.id)
        assert saved_book.title == "Updated title"

    async def test_delete_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        assert await book_repo_with_book.delete(valid_book.id) is None
        assert await book_repo_with_book.list_all() == []

    async def test_delete_unsaved_book(self, empty_book_repo: BookRepository):
        with pytest.raises(BookNotFound):
            await empty_book_repo.delete(uuid4())


class TestMemberRepository:
    async def test_get_list_without_member(
        self, empty_member_repo: MemberRepository
    ):
        assert await empty_member_repo.list_all() == []

    async def test_save_member(
        self, empty_member_repo: MemberRepository, valid_member: Member
    ):
        await empty_member_repo.save(valid_member)
        assert (
            await empty_member_repo.find_by_id(valid_member.id) == valid_member
        )

    async def test_read_unsaved_member(
        self, empty_member_repo: MemberRepository
    ):
        assert await empty_member_repo.find_by_id(uuid4()) is None

    async def test_read_member_by_email(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
        valid_email: Email,
    ):
        assert (
            await member_repo_with_member.find_by_email(valid_email)
            == valid_member
        )

    async def test_get_list_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        assert await member_repo_with_member.list_all() == [valid_member]

    async def test_get_immutable_list_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        member_list = await member_repo_with_member.list_all()
        member_list.append(valid_member)
        assert await member_repo_with_member.list_all() == [valid_member]

    async def test_update_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        valid_member.name = "Updated name"
        await member_repo_with_member.save(valid_member)
        saved_member = await member_repo_with_member.find_by_id(valid_member.id)
        assert saved_member.name == "Updated name"

    async def test_delete_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        assert await member_repo_with_member.delete(valid_member.id) is None
        assert await member_repo_with_member.list_all() == []

    async def test_delete_unsaved_member(
        self, empty_member_repo: MemberRepository
    ):
        with pytest.raises(MemberNotFound):
            await empty_member_repo.delete(uuid4())


class TestLoanRepository:
    async def test_get_list_without_loan(self, empty_loan_repo: LoanRepository):
        assert await empty_loan_repo.list_all() == []

    async def test_save_loan(
        self, empty_loan_repo: LoanRepository, valid_loan: Loan
    ):
        await empty_loan_repo.save(valid_loan)
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
        await loan_repo_with_loan.save(valid_loan)
        saved_loan = await loan_repo_with_loan.find_by_id(valid_loan.id)
        assert saved_loan.is_returned

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
        await loan_repo_with_loan.save(valid_loan)
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
        await empty_loan_repo.save(loan_1)
        await empty_loan_repo.save(loan_2)

        loans = await empty_loan_repo.find_by_member(member_id)
        assert set(loans) == {loan_1, loan_2}

    async def test_find_by_member_returns_empty_when_no_loans(
        self, empty_loan_repo: LoanRepository
    ):
        assert await empty_loan_repo.find_by_member(uuid4()) == []
