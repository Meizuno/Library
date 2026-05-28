from sqlalchemy import Boolean, Column, String, Table, Uuid
from sqlalchemy.sql.expression import false as sql_false

from library.shared.infrastructure.sql_metadata import metadata

members_table = Table(
    "members",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    # `server_default` ensures pre-existing rows from before this column
    # was added get a sane value; new rows always supply it explicitly.
    Column(
        "is_verified",
        Boolean,
        nullable=False,
        server_default=sql_false(),
    ),
)
