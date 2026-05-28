import asyncio
from typing import Annotated
from uuid import UUID

import typer

from library.member.application import (
    AddMemberCommand,
    AddMemberUseCase,
    DeleteMemberUseCase,
    ListMembersUseCase,
    MemberAlreadyExists,
    ReadMemberUseCase,
)
from library.member.domain import MemberNotFound
from library.shared.presentation.cli.container import cli_context
from library.shared.presentation.cli.output import (
    print_error,
    print_member,
    print_members,
    print_success,
)


app = typer.Typer(help="Manage members.")


@app.command("list")
def list_members() -> None:
    """List all members."""
    asyncio.run(_list_members())


async def _list_members() -> None:
    async with cli_context() as ctx:
        members = await ListMembersUseCase(ctx.members).execute()
    print_members(members)


@app.command("add")
def add_member(
    name: Annotated[str, typer.Option(help="Member name")],
    email: Annotated[str, typer.Option(help="Member email")],
    password: Annotated[
        str,
        typer.Option(
            help="Member password (min 8 chars)",
            prompt=True,
            hide_input=True,
        ),
    ],
) -> None:
    """Add a new member."""
    try:
        asyncio.run(_add_member(name, email, password))
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except MemberAlreadyExists as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _add_member(name: str, email: str, password: str) -> None:
    async with cli_context() as ctx:
        member = await AddMemberUseCase(ctx.members, ctx.hasher).execute(
            AddMemberCommand(name=name, email=email, password=password)
        )
    print_success(f"Added member {member.id}")
    print_member(member)


@app.command("read")
def read_member(member_id: UUID) -> None:
    """Read a member by id."""
    asyncio.run(_read_member(member_id))


async def _read_member(member_id: UUID) -> None:
    async with cli_context() as ctx:
        member = await ReadMemberUseCase(ctx.members).execute(member_id)
    if member is None:
        print_error(f"Member {member_id} not found")
        raise typer.Exit(code=1)
    print_member(member)


@app.command("delete")
def delete_member(member_id: UUID) -> None:
    """Delete a member by id."""
    try:
        asyncio.run(_delete_member(member_id))
    except MemberNotFound as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


async def _delete_member(member_id: UUID) -> None:
    async with cli_context() as ctx:
        await DeleteMemberUseCase(ctx.members).execute(member_id)
    print_success(f"Deleted member {member_id}")
