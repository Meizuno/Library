import pytest

from library.book.application import AddBookCommand
from library.book.domain import ISBN


@pytest.fixture
def book_command(valid_isbn: ISBN) -> AddBookCommand:
    return AddBookCommand(title="Title", author="Author", isbn=valid_isbn.value)
