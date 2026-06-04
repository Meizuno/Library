import pytest

from library.book.models import ISBN
from library.book.use_cases.add_book import AddBookCommand


@pytest.fixture
def book_command(valid_isbn: ISBN) -> AddBookCommand:
    return AddBookCommand(title="Title", author="Author", isbn=valid_isbn.value)
