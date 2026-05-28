from dataclasses import FrozenInstanceError

import pytest

from library.notification.domain import Notification


class TestNotification:
    def test_valid_notification(self):
        n = Notification(subject="Welcome", body="Hi there")
        assert n.subject == "Welcome"
        assert n.body == "Hi there"

    def test_empty_subject_is_allowed(self):
        # SMS / push channels often have no subject — must not block.
        n = Notification(subject="", body="Hi")
        assert n.subject == ""

    def test_empty_body_raises(self):
        with pytest.raises(ValueError, match="body cannot be empty"):
            Notification(subject="Welcome", body="")

    def test_is_frozen(self):
        n = Notification(subject="s", body="b")
        with pytest.raises(FrozenInstanceError):
            n.body = "new"  # type: ignore[misc]

    def test_equality_by_value(self):
        a = Notification(subject="s", body="b")
        b = Notification(subject="s", body="b")
        assert a == b

    def test_inequality_by_value(self):
        assert Notification(subject="s", body="b") != Notification(
            subject="s", body="other"
        )
