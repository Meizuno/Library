import pytest

from library.member.application import AddMemberCommand
from library.member.domain import Email


@pytest.fixture
def member_command(valid_email: Email) -> AddMemberCommand:
    return AddMemberCommand(
        name="Name", email=valid_email.value, password="password"
    )
