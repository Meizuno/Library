from dataclasses import FrozenInstanceError

import pytest

from library.domain import ISBN, Email


class TestISBN:
    def test_valid_isbn_with_dashes(self):
        valid_isbn = ISBN("978-3-16-148410-0")
        assert valid_isbn.value == "9783161484100"

    def test_valid_isbn_without_dashes(self):
        valid_isbn = ISBN("9783161484100")
        assert valid_isbn.value == "9783161484100"

    def test_valid_isbn_with_space(self):
        valid_isbn = ISBN("978 3 16 148410 0")
        assert valid_isbn.value == "9783161484100"

    def test_valid_isbn_old(self):
        valid_isbn = ISBN("0306406152")
        assert valid_isbn.value == "0306406152"

    def test_valid_isbn_hybrid_separators(self):
        valid_isbn = ISBN("978-3 16-148410 0")
        assert valid_isbn.value == "9783161484100"

    @pytest.mark.parametrize(
        "isbn",
        [
            "",
            "abcdefghij",
            "123456789",
            "12345678901",
            "123456789012",
            "12345678901234",
            "978-X-16-148410-0",
            "---",
        ],
    )
    def test_empty_isbn(self, isbn: str):
        with pytest.raises(ValueError, match="invalid ISBN"):
            _ = ISBN(isbn)

    def test_immutable_isbn(self):
        valid_isbn = ISBN("978-3-16-148410-0")
        with pytest.raises(FrozenInstanceError):
            valid_isbn.value = "978-3-16-148410-0"

    def test_equal_isbn(self):
        valid_isbn = ISBN("9783161484100")
        valid_isbn_with_dash = ISBN("978-3-16-148410-0")
        assert valid_isbn == valid_isbn_with_dash

    def test_non_equal_isbn(self):
        valid_isbn = ISBN("9783161484100")
        valid_isbn_with_dash = ISBN("978-3-16-148410-1")
        assert valid_isbn != valid_isbn_with_dash

    def test_hash_isbn(self):
        isbn_set = {ISBN("9783161484100"), ISBN("978-3-16-148410-0")}
        assert len(isbn_set) == 1


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
