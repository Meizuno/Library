from uuid import uuid4

from httpx import AsyncClient


class TestMemberAPI:
    async def test_create_member_return_201(self, client: AsyncClient):
        response = await client.post(
            "/members",
            json={
                "name": "Name",
                "email": "test@example.com",
                "password": "password",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Name"
        assert body["email"] == "test@example.com"
        assert "password" not in body
        assert "password_hash" not in body
        assert "id" in body

    async def test_create_duplicate_member_returns_409(
        self, client: AsyncClient
    ):
        payload = {
            "name": "Name",
            "email": "test@example.com",
            "password": "password",
        }
        await client.post("/members", json=payload)
        response = await client.post("/members", json=payload)
        assert response.status_code == 409

    async def test_create_invalid_email_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/members",
            json={
                "name": "Name",
                "email": "not-an-email",
                "password": "password",
            },
        )
        assert response.status_code == 422

    async def test_create_short_password_returns_422(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/members",
            json={
                "name": "Name",
                "email": "test@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    async def test_get_missing_member_returns_404(self, client: AsyncClient):
        response = await client.get(f"/members/{uuid4()}")
        assert response.status_code == 404

    async def test_delete_existing_member_returns_204(
        self, client: AsyncClient
    ):
        created = await client.post(
            "/members",
            json={
                "name": "Name",
                "email": "test@example.com",
                "password": "password",
            },
        )
        member_id = created.json()["id"]
        response = await client.delete(f"/members/{member_id}")
        assert response.status_code == 204
