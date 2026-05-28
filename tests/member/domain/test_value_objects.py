import pytest

from library.member.domain import Email, Password


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


class TestPassword:
    def test_valid_password(self):
        pw = Password("correcthorse")
        assert pw.value == "correcthorse"

    def test_exactly_min_length_is_valid(self):
        pw = Password("a" * Password.MIN_LENGTH)
        assert pw.value == "a" * Password.MIN_LENGTH

    @pytest.mark.parametrize("plain", ["", "short", "1234567"])
    def test_too_short_raises(self, plain: str):
        with pytest.raises(ValueError, match="password must be at least"):
            _ = Password(plain)

    def test_str_does_not_leak_value(self):
        pw = Password("correcthorse")
        assert "correcthorse" not in str(pw)
        assert str(pw) == "***"

    def test_password_is_frozen(self):
        pw = Password("correcthorse")
        with pytest.raises(Exception):
            pw.value = "other"  # type: ignore[misc]
