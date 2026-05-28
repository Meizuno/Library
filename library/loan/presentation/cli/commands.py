import asyncio
from typing import Annotated
from uuid import UUID

import typer

from library.book.domain import BookNotAvailable, BookNotFound
from library.loan.application import (
    BorrowBookCommand,
    BorrowBookUseCase,
    ReturnBookCommand,
    ReturnBookUseCase,
)
from library.loan.domain import LoanNotFound
from library.member.domain import MemberNotFound
from library.shared.presentation.cli.container import cli_context
from library.shared.presentation.cli.output import (
    print_error,
    print_loan,
    print_success,
)


app = typer.Typer(help="Manage loans (borrow / return).")


@app.command("borrow")
def borrow_book(
    book_id: Annotated[UUID, typer.Option(help="Book to borrow")],
    member_id: Annotated[UUID, typer.Option(help="Member borrowing the book")],
) -> None:
    """Borrow a book for a member."""
    try:
        asyncio.run(_borrow_book(book_id, member_id))
    except BookNotFound as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except MemberNotFound as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except BookNotAvailable as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _borrow_book(book_id: UUID, member_id: UUID) -> None:
    async with cli_context() as ctx:
        loan = await BorrowBookUseCase(
            ctx.books, ctx.members, ctx.loans, ctx.clock
        ).execute(BorrowBookCommand(book_id=book_id, member_id=member_id))
    print_success(f"Loan {loan.id} created")
    print_loan(loan)


@app.command("return")
def return_book(loan_id: UUID) -> None:
    """Return a borrowed book."""
    try:
        asyncio.run(_return_book(loan_id))
    except LoanNotFound as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _return_book(loan_id: UUID) -> None:
    async with cli_context() as ctx:
        loan = await ReturnBookUseCase(ctx.loans, ctx.clock).execute(
            ReturnBookCommand(loan_id=loan_id)
        )
    print_success(f"Loan {loan.id} returned")
    print_loan(loan)
