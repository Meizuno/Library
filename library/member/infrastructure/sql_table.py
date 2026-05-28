from sqlalchemy import Table, Column, String, Uuid

from library.shared.infrastructure.sql_metadata import metadata

members_table = Table(
    "members",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
)
