from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from library.book.domain import Book, BookNotAvailable, BookNotFound, BookRepository
from library.loan.application import BorrowBookCommand, BorrowBookUseCase
from library.loan.domain import LoanRepository
from library.member.domain import Member, MemberNotFound, MemberRepository
from library.shared.application import Clock


class TestBorrowBookUseCase:
    async def test_borrow_book_success(
        self,
        book_repo_with_book: BookRepository,
        member_repo_with_member: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        now: datetime,
        valid_book: Book,
        valid_member: Member,
    ):
        use_case = BorrowBookUseCase(
            book_repo_with_book, member_repo_with_member, loan_repo, clock
        )

        loan = await use_case.execute(
            BorrowBookCommand(book_id=valid_book.id, member_id=valid_member.id)
        )

        assert loan.book_id == valid_book.id
        assert loan.member_id == valid_member.id
        assert loan.loaned_at == now
        assert loan.due_at == now + timedelta(days=14)
        assert loan.returned_at is None
        assert await loan_repo.find_by_id(loan.id) == loan

    async def test_borrow_book_uses_custom_period(
        self,
        book_repo_with_book: BookRepository,
        member_repo_with_member: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        now: datetime,
        valid_book: Book,
        valid_member: Member,
    ):
        use_case = BorrowBookUseCase(
            book_repo_with_book,
            member_repo_with_member,
            loan_repo,
            clock,
            loan_period_days=7,
        )

        loan = await use_case.execute(
            BorrowBookCommand(book_id=valid_book.id, member_id=valid_member.id)
        )

        assert loan.due_at == now + timedelta(days=7)

    async def test_borrow_missing_book_raises(
        self,
        book_repo: BookRepository,
        member_repo_with_member: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        valid_member: Member,
    ):
        use_case = BorrowBookUseCase(
            book_repo, member_repo_with_member, loan_repo, clock
        )

        with pytest.raises(BookNotFound):
            await use_case.execute(
                BorrowBookCommand(book_id=uuid4(), member_id=valid_member.id)
            )

    async def test_borrow_missing_member_raises(
        self,
        book_repo_with_book: BookRepository,
        member_repo: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        valid_book: Book,
    ):
        use_case = BorrowBookUseCase(
            book_repo_with_book, member_repo, loan_repo, clock
        )

        with pytest.raises(MemberNotFound):
            await use_case.execute(
                BorrowBookCommand(book_id=valid_book.id, member_id=uuid4())
            )

    async def test_borrow_already_loaned_book_raises(
        self,
        book_repo_with_book: BookRepository,
        member_repo_with_member: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        valid_book: Book,
        valid_member: Member,
    ):
        use_case = BorrowBookUseCase(
            book_repo_with_book, member_repo_with_member, loan_repo, clock
        )
        await use_case.execute(
            BorrowBookCommand(book_id=valid_book.id, member_id=valid_member.id)
        )

        with pytest.raises(BookNotAvailable):
            await use_case.execute(
                BorrowBookCommand(
                    book_id=valid_book.id, member_id=valid_member.id
                )
            )

    async def test_borrow_after_return_succeeds(
        self,
        book_repo_with_book: BookRepository,
        member_repo_with_member: MemberRepository,
        loan_repo: LoanRepository,
        clock: Clock,
        valid_book: Book,
        valid_member: Member,
        now: datetime,
    ):
        use_case = BorrowBookUseCase(
            book_repo_with_book, member_repo_with_member, loan_repo, clock
        )
        first_loan = await use_case.execute(
            BorrowBookCommand(book_id=valid_book.id, member_id=valid_member.id)
        )
        first_loan.mark_returned(now + timedelta(days=1))
        await loan_repo.update(first_loan)

        second_loan = await use_case.execute(
            BorrowBookCommand(book_id=valid_book.id, member_id=valid_member.id)
        )

        assert second_loan.id != first_loan.id
        assert second_loan.book_id == valid_book.id
