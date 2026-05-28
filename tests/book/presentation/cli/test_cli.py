from uuid import uuid4

from typer.testing import CliRunner

from library.shared.presentation.cli.main import app


def test_books_list_empty(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["books", "list"])
    assert result.exit_code == 0
    assert "No books" in result.output


def test_books_add_then_list(runner: CliRunner, cli_setup):
    add_result = runner.invoke(
        app,
        [
            "books",
            "add",
            "--title",
            "The Title",
            "--author",
            "An Author",
            "--isbn",
            "978-3-16-148410-0",
        ],
    )
    assert add_result.exit_code == 0
    assert "Added book" in add_result.output

    list_result = runner.invoke(app, ["books", "list"])
    assert list_result.exit_code == 0
    assert "The Title" in list_result.output
    assert "An Author" in list_result.output
    assert "9783161484100" in list_result.output


def test_books_add_duplicate_isbn_exits_with_error(
    runner: CliRunner, cli_setup
):
    args = [
        "books",
        "add",
        "--title",
        "T",
        "--author",
        "A",
        "--isbn",
        "978-3-16-148410-0",
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0

    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "Error" in second.output


def test_books_add_invalid_isbn_exits_with_error(
    runner: CliRunner, cli_setup
):
    result = runner.invoke(
        app,
        [
            "books",
            "add",
            "--title",
            "T",
            "--author",
            "A",
            "--isbn",
            "not-an-isbn",
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_books_read_missing_exits_with_error(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["books", "read", str(uuid4())])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_books_delete_missing_exits_with_error(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["books", "delete", str(uuid4())])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_books_add_read_delete_roundtrip(runner: CliRunner, cli_setup):
    add_result = runner.invoke(
        app,
        [
            "books",
            "add",
            "--title",
            "Roundtrip",
            "--author",
            "Tester",
            "--isbn",
            "978-3-16-148410-0",
        ],
    )
    assert add_result.exit_code == 0

    # extract id from "Added book <uuid>"
    book_id = add_result.output.split("Added book")[1].split()[0].strip()

    read_result = runner.invoke(app, ["books", "read", book_id])
    assert read_result.exit_code == 0
    assert "Roundtrip" in read_result.output

    delete_result = runner.invoke(app, ["books", "delete", book_id])
    assert delete_result.exit_code == 0
    assert "Deleted" in delete_result.output

    list_result = runner.invoke(app, ["books", "list"])
    assert "No books" in list_result.output
