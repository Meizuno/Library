import asyncio
from typing import Annotated
from uuid import UUID

import typer

from library.application import AddBookCommand, BookAlreadyExists
from library.application.use_cases import (
    AddBookUseCase,
    ListBooksUseCase,
    ReadBookUseCase,
    DeleteBookUseCase,
)
from library.domain import BookNotFound
from library.cli.container import cli_context
from library.cli.output import (
    print_book,
    print_books,
    print_success,
    print_error,
)


app = typer.Typer(help="Manage books.")


@app.command("list")
def list_books() -> None:
    """List all books."""
    asyncio.run(_list_books())


async def _list_books() -> None:
    async with cli_context() as ctx:
        books = await ListBooksUseCase(ctx.books).execute()
    print_books(books)


@app.command("add")
def add_book(
    title: Annotated[str, typer.Option(help="Book title")],
    author: Annotated[str, typer.Option(help="Book author")],
    isbn: Annotated[str, typer.Option(help="ISBN (with or without dashes)")],
) -> None:
    """Add a new book."""
    try:
        asyncio.run(_add_book(title, author, isbn))
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except BookAlreadyExists as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _add_book(title: str, author: str, isbn: str) -> None:
    async with cli_context() as ctx:
        book = await AddBookUseCase(ctx.books).execute(
            AddBookCommand(title=title, author=author, isbn=isbn)
        )
    print_success(f"Added book {book.id}")
    print_book(book)


@app.command("read")
def read_book(book_id: UUID) -> None:
    """Read a book by id."""
    asyncio.run(_read_book(book_id))


async def _read_book(book_id: UUID) -> None:
    async with cli_context() as ctx:
        book = await ReadBookUseCase(ctx.books).execute(book_id)
    if book is None:
        print_error(f"Book {book_id} not found")
        raise typer.Exit(code=1)
    print_book(book)


@app.command("delete")
def delete_book(book_id: UUID) -> None:
    """Delete a book by id."""
    try:
        asyncio.run(_delete_book(book_id))
    except BookNotFound as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _delete_book(book_id: UUID) -> None:
    async with cli_context() as ctx:
        await DeleteBookUseCase(ctx.books).execute(book_id)
    print_success(f"Deleted book {book_id}")
