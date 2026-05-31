from sqlalchemy import Column, DateTime, String, Table, Uuid

from library.shared.infrastructure.sql_metadata import metadata

books_table = Table(
    "books",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("isbn", String, nullable=False, unique=True),
    Column("description", String, nullable=False, server_default=""),
    # Soft-delete marker. NULL = active row. Set to the server's
    # current timestamp on `delete()`; reads filter rows where this
    # is non-NULL so deleted books are invisible to use cases.
    Column("deleted_at", DateTime, nullable=True),
)
