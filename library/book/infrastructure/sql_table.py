from sqlalchemy import Table, Column, String, Uuid

from library.shared.infrastructure.sql_metadata import metadata

books_table = Table(
    "books",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("isbn", String, nullable=False, unique=True),
    Column("description", String, nullable=False, server_default=""),
)
