import pytest

from library.member.domain import Email


class TestEmail:
    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "first.last@example.com",
            "user@mail.example.co.uk",
            "user123@example.com",
        ],
    )
    def test_valid_email(self, email: str):
        valid_email = Email(email)
        assert valid_email.value == email

    @pytest.mark.parametrize(
        "email",
        [
            "",
            "no-at-sign",
            "@example.com",
            "user@",
            "user@example",
            " ",
            "a@b@c.com",
        ],
    )
    def test_invalid_email(self, email: str):
        with pytest.raises(ValueError, match=f"invalid email: {email!r}"):
            _ = Email(email)
