import asyncio
from typing import Annotated
from uuid import UUID

import typer

from library.application import BorrowBookCommand, ReturnBookCommand
from library.application.use_cases import (
    BorrowBookUseCase,
    ReturnBookUseCase,
)
from library.domain import (
    BookNotFound,
    BookNotAvailable,
    MemberNotFound,
    LoanNotFound,
)
from library.cli.container import cli_context
from library.cli.output import print_loan, print_success, print_error


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
