from uuid import UUID, uuid4

import pytest

from library.domain import Book, Member, ISBN, Email


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


class TestMember:
    def test_valid_member(self, valid_email: Email):
        member = Member(name="Name", email=valid_email)

        assert isinstance(member.id, UUID)
        assert member.name == "Name"
        assert member.email == valid_email
        assert member.email.value == valid_email.value

    def test_each_member_has_unique_id(self, valid_email):
        member_1 = Member(name="A", email=valid_email)
        member_2 = Member(name="B", email=valid_email)
        assert member_1.id != member_2.id

    def test_member_id_can_be_set_after_construction(self, valid_email):
        custom_id = uuid4()
        member = Member(name="X", email=valid_email)
        member.id = custom_id
        assert member.id == custom_id

    def test_id_is_not_settable_via_constructor(self, valid_email):
        with pytest.raises(TypeError):
            Member(  # pylint: disable=unexpected-keyword-arg
                id=uuid4(),
                name="Name",
                email=valid_email,
            )

    @pytest.mark.parametrize("name", ["", " "])
    def test_empty_name(self, name, valid_email):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Member(name=name, email=valid_email)

    def test_member_is_hashable(self, valid_email):
        """__hash__ працює — Member можна покласти в set/dict."""
        member = Member(name="X", email=valid_email)
        s = {member}
        assert member in s

    def test_members_with_same_id_share_hash(self, valid_email):
        """Два Member з однаковим id мають однаковий hash."""
        shared_id = uuid4()
        m_1 = Member(name="A", email=valid_email)
        m_2 = Member(name="B", email=valid_email)
        m_1.id = shared_id
        m_2.id = shared_id
        assert hash(m_1) == hash(m_2)
        assert len({m_1, m_2}) == 1
