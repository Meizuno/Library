from uuid import UUID, uuid4

import pytest

from library.book.domain import ISBN, Book


class TestBook:
    def test_valid_book(self, valid_isbn: ISBN):
        book = Book(title="Title", author="Author", isbn=valid_isbn)

        assert isinstance(book.id, UUID)
        assert book.title == "Title"
        assert book.author == "Author"
        assert book.isbn == valid_isbn
        assert book.isbn.value == valid_isbn.value

    def test_each_book_has_unique_id(self, valid_isbn):
        """UUID генерується автоматично — два Book ніколи не співпадають за id."""
        book_1 = Book(title="X", author="Y", isbn=valid_isbn)
        book_2 = Book(title="X", author="Y", isbn=valid_isbn)
        assert book_1.id != book_2.id

    def test_book_id_can_be_set_after_construction(self, valid_isbn):
        """id ховається від __init__, але mutable — Repository може його замінити при load з БД."""
        custom_id = uuid4()
        book = Book(title="X", author="Y", isbn=valid_isbn)
        book.id = custom_id
        assert book.id == custom_id

    def test_id_is_not_settable_via_constructor(self, valid_isbn):
        with pytest.raises(TypeError):
            Book(  # pylint: disable=unexpected-keyword-arg
                id=uuid4(),
                title="Title",
                author="Author",
                isbn=valid_isbn,
            )

    @pytest.mark.parametrize("title", ["", " "])
    def test_empty_title(self, title, valid_isbn):
        with pytest.raises(ValueError, match="title cannot be empty"):
            Book(title=title, author="Author", isbn=valid_isbn)

    @pytest.mark.parametrize("author", ["", " "])
    def test_empty_author(self, author, valid_isbn):
        with pytest.raises(ValueError, match="author cannot be empty"):
            Book(title="Title", author=author, isbn=valid_isbn)

    def test_non_immutable_book(self, valid_isbn):
        book = Book(title="Title", author="Author", isbn=valid_isbn)
        book.title = "New Title"
        book.author = "New Author"

        assert book.title == "New Title"
        assert book.author == "New Author"

    def test_equal_books_when_id_shared(self, valid_isbn):
        """Два Book з однаковим id І полями — рівні (id присвоюється після створення)."""
        shared_id = uuid4()
        book_1 = Book(title="Title", author="Author", isbn=valid_isbn)
        book_2 = Book(title="Title", author="Author", isbn=valid_isbn)
        book_1.id = shared_id
        book_2.id = shared_id
        assert book_1 == book_2

    def test_non_equal_books_by_id(self, valid_isbn):
        """Два Book з різними id (auto-generated) — НЕ рівні."""
        book_1 = Book(title="Title", author="Author", isbn=valid_isbn)
        book_2 = Book(title="Title", author="Author", isbn=valid_isbn)
        assert book_1 != book_2

    def test_book_is_hashable(self, valid_isbn):
        """__hash__ працює — Book можна покласти в set/dict."""
        book = Book(title="X", author="Y", isbn=valid_isbn)
        s = {book}
        assert book in s

    def test_books_with_same_id_share_hash(self, valid_isbn):
        """Два Book з однаковим id мають однаковий hash — дедуплікація в set."""
        shared_id = uuid4()
        book_1 = Book(title="X", author="Y", isbn=valid_isbn)
        book_2 = Book(title="Z", author="W", isbn=valid_isbn)
        book_1.id = shared_id
        book_2.id = shared_id
        assert hash(book_1) == hash(book_2)
        assert len({book_1, book_2}) == 1

    def test_description_defaults_to_empty(self, valid_isbn):
        book = Book(title="X", author="Y", isbn=valid_isbn)
        assert book.description == ""

    def test_description_is_stripped(self, valid_isbn):
        book = Book(
            title="X",
            author="Y",
            isbn=valid_isbn,
            description="  a classic   ",
        )
        assert book.description == "a classic"

    def test_description_can_be_provided(self, valid_isbn):
        book = Book(
            title="X", author="Y", isbn=valid_isbn, description="Nice"
        )
        assert book.description == "Nice"
