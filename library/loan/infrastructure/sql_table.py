from sqlalchemy import Column, DateTime, ForeignKey, Index, Table, Uuid

from library.shared.infrastructure.sql_metadata import metadata

loans_table = Table(
    "loans",
    metadata,
    Column("id", Uuid, primary_key=True),
    # FK with ondelete="RESTRICT" prevents the database from removing
    # a referenced book or member while loans still point at it.
    # In normal app flow this never fires because books and members
    # are soft-deleted (their rows stay physically present); the FK
    # is the safety net for raw SQL, migrations, or buggy code paths
    # that bypass the soft-delete logic.
    Column(
        "book_id",
        Uuid,
        ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "member_id",
        Uuid,
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("loaned_at", DateTime, nullable=False),
    Column("due_at", DateTime, nullable=False),
    Column("returned_at", DateTime, nullable=True),
    Index("ix_loans_book_id", "book_id"),
    Index("ix_loans_member_id", "member_id"),
)
