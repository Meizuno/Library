from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Uuid,
)

from library.shared.infrastructure.sql_metadata import metadata

refresh_tokens_table = Table(
    "refresh_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    # FK with ondelete="RESTRICT" mirrors loans.member_id: in normal app
    # flow nothing ever fires it (members are soft-deleted, their row
    # stays), but it forbids any raw-SQL or future hard-delete path
    # that would otherwise leave orphan refresh-token rows behind.
    Column(
        "member_id",
        Uuid,
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("token_hash", String, nullable=False, unique=True),
    Column("expires_at", DateTime, nullable=False),
    Column("revoked_at", DateTime, nullable=True),
    Index("ix_refresh_tokens_member_id", "member_id"),
)
