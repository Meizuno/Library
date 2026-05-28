from uuid import uuid4

from typer.testing import CliRunner

from library.shared.presentation.cli.main import app


def test_members_list_empty(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["members", "list"])
    assert result.exit_code == 0
    assert "No members" in result.output


def test_members_add_then_list(runner: CliRunner, cli_setup):
    add_result = runner.invoke(
        app,
        [
            "members",
            "add",
            "--name",
            "Alice",
            "--email",
            "alice@example.com",
            "--password",
            "password",
        ],
    )
    assert add_result.exit_code == 0
    assert "Added member" in add_result.output

    list_result = runner.invoke(app, ["members", "list"])
    assert "Alice" in list_result.output
    assert "alice@example.com" in list_result.output


def test_members_add_duplicate_email_exits_with_error(
    runner: CliRunner, cli_setup
):
    args = [
        "members",
        "add",
        "--name",
        "Bob",
        "--email",
        "bob@example.com",
        "--password",
        "password",
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0

    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "Error" in second.output


def test_members_add_invalid_email_exits_with_error(
    runner: CliRunner, cli_setup
):
    result = runner.invoke(
        app,
        [
            "members",
            "add",
            "--name",
            "Bob",
            "--email",
            "not-an-email",
            "--password",
            "password",
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_members_add_short_password_exits_with_error(
    runner: CliRunner, cli_setup
):
    result = runner.invoke(
        app,
        [
            "members",
            "add",
            "--name",
            "Bob",
            "--email",
            "bob@example.com",
            "--password",
            "short",
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_members_read_missing_exits_with_error(runner: CliRunner, cli_setup):
    result = runner.invoke(app, ["members", "read", str(uuid4())])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_members_delete_missing_exits_with_error(
    runner: CliRunner, cli_setup
):
    result = runner.invoke(app, ["members", "delete", str(uuid4())])
    assert result.exit_code == 1
    assert "Error" in result.output
