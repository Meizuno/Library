from sqlalchemy import Table, Column, Uuid, DateTime, Index

from library.shared.infrastructure.sql_metadata import metadata

loans_table = Table(
    "loans",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("book_id", Uuid, nullable=False),
    Column("member_id", Uuid, nullable=False),
    Column("loaned_at", DateTime, nullable=False),
    Column("due_at", DateTime, nullable=False),
    Column("returned_at", DateTime, nullable=True),
    Index("ix_loans_book_id", "book_id"),
    Index("ix_loans_member_id", "member_id"),
)
