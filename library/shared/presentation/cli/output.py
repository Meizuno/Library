from rich.console import Console
from rich.table import Table

from library.book.domain import Book
from library.loan.domain import Loan
from library.member.domain import Member


console = Console()
err_console = Console(stderr=True)


def print_book(book: Book) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("id", str(book.id))
    table.add_row("title", book.title)
    table.add_row("author", book.author)
    table.add_row("isbn", book.isbn.value)
    console.print(table)


def print_books(books: list[Book]) -> None:
    if not books:
        console.print("[dim]No books.[/dim]")
        return
    table = Table(title="Books")
    table.add_column("id", style="cyan")
    table.add_column("title")
    table.add_column("author")
    table.add_column("isbn", style="green")
    for book in books:
        table.add_row(str(book.id), book.title, book.author, book.isbn.value)
    console.print(table)


def print_member(member: Member) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("id", str(member.id))
    table.add_row("name", member.name)
    table.add_row("email", member.email.value)
    console.print(table)


def print_members(members: list[Member]) -> None:
    if not members:
        console.print("[dim]No members.[/dim]")
        return
    table = Table(title="Members")
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("email", style="green")
    for member in members:
        table.add_row(str(member.id), member.name, member.email.value)
    console.print(table)


def print_loan(loan: Loan) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("id", str(loan.id))
    table.add_row("book_id", str(loan.book_id))
    table.add_row("member_id", str(loan.member_id))
    table.add_row("loaned_at", loan.loaned_at.isoformat())
    table.add_row("due_at", loan.due_at.isoformat())
    table.add_row(
        "returned_at",
        loan.returned_at.isoformat() if loan.returned_at else "—",
    )
    console.print(table)


def print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def print_error(message: str) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {message}")
