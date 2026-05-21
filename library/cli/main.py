import typer

from library.cli.commands import book, member, loan


app = typer.Typer(
    help="Library — command-line interface.",
    no_args_is_help=True,
)
app.add_typer(book.app, name="books")
app.add_typer(member.app, name="members")
app.add_typer(loan.app, name="loans")


if __name__ == "__main__":
    app()
