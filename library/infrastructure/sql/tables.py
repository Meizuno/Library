from sqlalchemy import MetaData, Table, Column, String, Uuid, DateTime, Index

metadata = MetaData()

books_table = Table(
    "books",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("isbn", String, nullable=False, unique=True),
)

members_table = Table(
    "members",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
)

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
