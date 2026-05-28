from sqlalchemy import Column, DateTime, Index, String, Table, Uuid

from library.shared.infrastructure.sql_metadata import metadata

refresh_tokens_table = Table(
    "refresh_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("member_id", Uuid, nullable=False),
    Column("token_hash", String, nullable=False, unique=True),
    Column("expires_at", DateTime, nullable=False),
    Column("revoked_at", DateTime, nullable=True),
    Index("ix_refresh_tokens_member_id", "member_id"),
)
