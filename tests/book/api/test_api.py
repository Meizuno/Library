from datetime import datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from library.loan.models import Loan
from library.loan.ports import LoanRepository


class TestBooksAPI:
    async def test_create_book_returns_201(self, client: AsyncClient):
        response = await client.post(
            "/books",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Title"
        assert body["author"] == "Author"
        assert body["isbn"] == "9783161484100"
        assert body["description"] == ""
        assert body["is_available"] is True  # new book, no loans yet
        assert "id" in body

    async def test_create_book_with_description_returns_201(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/books",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
                "description": "A summary",
            },
        )

        assert response.status_code == 201
        assert response.json()["description"] == "A summary"

    async def test_update_book_returns_200(self, client: AsyncClient):
        created = await client.post(
            "/books",
            json={
                "title": "Old",
                "author": "Old A",
                "isbn": "978-3-16-148410-0",
                "description": "old desc",
            },
        )
        book_id = created.json()["id"]

        response = await client.put(
            f"/books/{book_id}",
            json={
                "title": "New",
                "author": "New A",
                "description": "new desc",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "New"
        assert body["author"] == "New A"
        assert body["description"] == "new desc"
        assert body["isbn"] == "9783161484100"

    async def test_update_missing_book_returns_404(self, client: AsyncClient):
        response = await client.put(
            f"/books/{uuid4()}",
            json={"title": "T", "author": "A", "description": ""},
        )
        assert response.status_code == 404

    async def test_update_book_with_empty_title_returns_422(
        self, client: AsyncClient
    ):
        created = await client.post(
            "/books",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )
        book_id = created.json()["id"]

        response = await client.put(
            f"/books/{book_id}",
            json={"title": "", "author": "A", "description": ""},
        )
        assert response.status_code == 422

    async def test_create_duplicate_book_returns_409(self, client: AsyncClient):
        payload = {
            "title": "Title",
            "author": "Author",
            "isbn": "978-3-16-148410-0",
        }
        await client.post("/books", json=payload)
        response = await client.post("/books", json=payload)
        assert response.status_code == 409

    async def test_create_invalid_isbn_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/books",
            json={"title": "Title", "author": "Author", "isbn": "not-an-isbn"},
        )
        assert response.status_code == 422

    async def test_get_missing_book_returns_404(self, client: AsyncClient):
        response = await client.get(f"/books/{uuid4()}")
        assert response.status_code == 404

    async def test_delete_existing_book_returns_204(self, client: AsyncClient):
        created = await client.post(
            "/books",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )
        book_id = created.json()["id"]
        response = await client.delete(f"/books/{book_id}")
        assert response.status_code == 204

    async def test_read_book_is_available_true_when_no_active_loan(
        self, client: AsyncClient
    ):
        created = await client.post(
            "/books",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )
        book_id = created.json()["id"]

        response = await client.get(f"/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["is_available"] is True

    async def test_read_book_is_available_false_when_active_loan_exists(
        self,
        client: AsyncClient,
        loan_repo: LoanRepository,
    ):
        # Seed a book via the API, then seed an active loan against it
        # directly through the (shared) loan_repo fixture — the same
        # repo the LoanBookAvailability port reads from.
        created = await client.post(
            "/books",
            json={
                "title": "Borrowed Book",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )
        book_id = UUID(created.json()["id"])

        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        await loan_repo.create(
            Loan(
                book_id=book_id,
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=loaned_at + timedelta(days=14),
                # returned_at is None — active loan
            )
        )

        response = await client.get(f"/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["is_available"] is False

    async def test_list_books_includes_is_available_per_book(
        self,
        client: AsyncClient,
        loan_repo: LoanRepository,
    ):
        # Seed two books — one with an active loan, one without.
        book_a = (await client.post(
            "/books",
            json={
                "title": "Available Book",
                "author": "Author",
                "isbn": "978-3-16-148410-0",
            },
        )).json()
        book_b = (await client.post(
            "/books",
            json={
                "title": "Loaned Book",
                "author": "Author",
                "isbn": "978-3-16-148411-0",
            },
        )).json()

        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        await loan_repo.create(
            Loan(
                book_id=UUID(book_b["id"]),
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=loaned_at + timedelta(days=14),
            )
        )

        listed = (await client.get("/books")).json()
        by_id = {b["id"]: b for b in listed}
        assert by_id[book_a["id"]]["is_available"] is True
        assert by_id[book_b["id"]]["is_available"] is False

    async def test_list_books_with_search_filters_results(
        self, client: AsyncClient
    ):
        # Seed two books — one matches a title search, one matches an author
        # search, neither matches a third query.
        await client.post(
            "/books",
            json={
                "title": "Harry Potter",
                "author": "J.K. Rowling",
                "isbn": "978-3-16-148410-0",
            },
        )
        await client.post(
            "/books",
            json={
                "title": "The Hobbit",
                "author": "J.R.R. Tolkien",
                "isbn": "978-3-16-148411-0",
            },
        )

        by_title = (await client.get("/books?search=potter")).json()
        assert [b["title"] for b in by_title] == ["Harry Potter"]

        by_author = (await client.get("/books?search=tolkien")).json()
        assert [b["author"] for b in by_author] == ["J.R.R. Tolkien"]

        no_match = (await client.get("/books?search=xyzzy")).json()
        assert no_match == []

        no_param = (await client.get("/books")).json()
        assert len(no_param) == 2
