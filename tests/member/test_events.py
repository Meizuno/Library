from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from library.member.events import MemberRegistered


class TestMemberRegistered:
    def test_holds_member_facts(self):
        member_id = uuid4()
        event = MemberRegistered(
            member_id=member_id, name="Name", email="user@example.com"
        )
        assert event.member_id == member_id
        assert event.name == "Name"
        assert event.email == "user@example.com"

    def test_is_frozen(self):
        event = MemberRegistered(
            member_id=uuid4(), name="Name", email="user@example.com"
        )
        with pytest.raises(FrozenInstanceError):
            # See tests/book/test_models.py::test_immutable_isbn for the
            # mypy/setattr rationale.
            setattr(event, "email", "other@example.com")  # noqa: B010

    def test_equality_by_value(self):
        member_id = uuid4()
        a = MemberRegistered(
            member_id=member_id, name="Name", email="user@example.com"
        )
        b = MemberRegistered(
            member_id=member_id, name="Name", email="user@example.com"
        )
        assert a == b
