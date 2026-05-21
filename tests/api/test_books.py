from httpx import AsyncClient


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
        assert "id" in body

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
        from uuid import uuid4

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
