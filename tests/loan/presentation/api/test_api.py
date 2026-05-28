from datetime import timedelta
from uuid import uuid4

from httpx import AsyncClient


async def _create_book(client: AsyncClient) -> str:
    response = await client.post(
        "/books",
        json={
            "title": "Title",
            "author": "Author",
            "isbn": "978-3-16-148410-0",
        },
    )
    return response.json()["id"]


async def _create_member(client: AsyncClient) -> str:
    response = await client.post(
        "/members", json={"name": "Name", "email": "user@example.com"}
    )
    return response.json()["id"]


class TestLoansAPI:
    async def test_borrow_book_returns_201(self, client: AsyncClient, now):
        book_id = await _create_book(client)
        member_id = await _create_member(client)

        response = await client.post(
            "/loans", json={"book_id": book_id, "member_id": member_id}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["book_id"] == book_id
        assert body["member_id"] == member_id
        assert body["loaned_at"] == now.isoformat()
        assert body["due_at"] == (now + timedelta(days=14)).isoformat()
        assert body["returned_at"] is None
        assert "id" in body

    async def test_borrow_missing_book_returns_404(self, client: AsyncClient):
        member_id = await _create_member(client)
        response = await client.post(
            "/loans",
            json={"book_id": str(uuid4()), "member_id": member_id},
        )
        assert response.status_code == 404

    async def test_borrow_missing_member_returns_404(
        self, client: AsyncClient
    ):
        book_id = await _create_book(client)
        response = await client.post(
            "/loans",
            json={"book_id": book_id, "member_id": str(uuid4())},
        )
        assert response.status_code == 404

    async def test_borrow_already_loaned_book_returns_409(
        self, client: AsyncClient
    ):
        book_id = await _create_book(client)
        member_id = await _create_member(client)
        await client.post(
            "/loans", json={"book_id": book_id, "member_id": member_id}
        )

        response = await client.post(
            "/loans", json={"book_id": book_id, "member_id": member_id}
        )

        assert response.status_code == 409

    async def test_return_book_returns_200(self, client: AsyncClient, now):
        book_id = await _create_book(client)
        member_id = await _create_member(client)
        loan = (
            await client.post(
                "/loans",
                json={"book_id": book_id, "member_id": member_id},
            )
        ).json()

        response = await client.post(f"/loans/{loan['id']}/return")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == loan["id"]
        assert body["returned_at"] == now.isoformat()

    async def test_return_missing_loan_returns_404(
        self, client: AsyncClient
    ):
        response = await client.post(f"/loans/{uuid4()}/return")
        assert response.status_code == 404

    async def test_return_already_returned_loan_returns_422(
        self, client: AsyncClient
    ):
        book_id = await _create_book(client)
        member_id = await _create_member(client)
        loan = (
            await client.post(
                "/loans",
                json={"book_id": book_id, "member_id": member_id},
            )
        ).json()
        await client.post(f"/loans/{loan['id']}/return")

        response = await client.post(f"/loans/{loan['id']}/return")

        assert response.status_code == 422

    async def test_borrow_after_return_succeeds(self, client: AsyncClient):
        book_id = await _create_book(client)
        member_id = await _create_member(client)
        loan = (
            await client.post(
                "/loans",
                json={"book_id": book_id, "member_id": member_id},
            )
        ).json()
        await client.post(f"/loans/{loan['id']}/return")

        response = await client.post(
            "/loans", json={"book_id": book_id, "member_id": member_id}
        )

        assert response.status_code == 201
        assert response.json()["id"] != loan["id"]
