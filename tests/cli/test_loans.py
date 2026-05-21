from uuid import uuid4

from typer.testing import CliRunner

from library.cli.main import app


def _create_book(runner: CliRunner) -> str:
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
            "978-3-16-148410-0",
        ],
    )
    assert result.exit_code == 0
    return result.output.split("Added book")[1].split()[0].strip()


def _create_member(runner: CliRunner) -> str:
    result = runner.invoke(
        app,
        [
            "members",
            "add",
            "--name",
            "Alice",
            "--email",
            "alice@example.com",
        ],
    )
    assert result.exit_code == 0
    return result.output.split("Added member")[1].split()[0].strip()


def test_loans_borrow_success(runner: CliRunner, cli_setup):
    book_id = _create_book(runner)
    member_id = _create_member(runner)

    result = runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            book_id,
            "--member-id",
            member_id,
        ],
    )
    assert result.exit_code == 0
    assert "Loan" in result.output


def test_loans_borrow_missing_book_exits_with_error(
    runner: CliRunner, cli_setup
):
    member_id = _create_member(runner)
    result = runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            str(uuid4()),
            "--member-id",
            member_id,
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_loans_borrow_missing_member_exits_with_error(
    runner: CliRunner, cli_setup
):
    book_id = _create_book(runner)
    result = runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            book_id,
            "--member-id",
            str(uuid4()),
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_loans_borrow_already_loaned_exits_with_error(
    runner: CliRunner, cli_setup
):
    book_id = _create_book(runner)
    member_id = _create_member(runner)
    runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            book_id,
            "--member-id",
            member_id,
        ],
    )

    second = runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            book_id,
            "--member-id",
            member_id,
        ],
    )
    assert second.exit_code == 1
    assert "Error" in second.output


def test_loans_return_missing_exits_with_error(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["loans", "return", str(uuid4())])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_loans_borrow_then_return(runner: CliRunner, cli_setup):
    book_id = _create_book(runner)
    member_id = _create_member(runner)

    borrow_result = runner.invoke(
        app,
        [
            "loans",
            "borrow",
            "--book-id",
            book_id,
            "--member-id",
            member_id,
        ],
    )
    assert borrow_result.exit_code == 0
    loan_id = borrow_result.output.split("Loan")[1].split()[0].strip()

    return_result = runner.invoke(app, ["loans", "return", loan_id])
    assert return_result.exit_code == 0
    assert "returned" in return_result.output.lower()
