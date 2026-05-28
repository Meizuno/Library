import typer

from library.book.presentation.cli.commands import app as book_app
from library.loan.presentation.cli.commands import app as loan_app
from library.member.presentation.cli.commands import app as member_app


app = typer.Typer(
    help="Library — command-line interface.",
    no_args_is_help=True,
)
app.add_typer(book_app, name="books")
app.add_typer(member_app, name="members")
app.add_typer(loan_app, name="loans")


if __name__ == "__main__":
    app()
