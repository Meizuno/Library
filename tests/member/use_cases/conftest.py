import pytest

from library.member.models import Email
from library.member.use_cases.add_member import AddMemberCommand


@pytest.fixture
def member_command(valid_email: Email) -> AddMemberCommand:
    return AddMemberCommand(
        name="Name", email=valid_email.value, password="password"
    )
