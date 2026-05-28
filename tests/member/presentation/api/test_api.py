from uuid import uuid4

from httpx import AsyncClient

from library.auth.domain import TokenIssuer
from library.member.domain import VerificationTokenIssuer


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
        assert body["is_verified"] is False  # new members start unverified
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


class TestMemberVerifyAPI:
    async def test_verify_with_valid_token_returns_200(
        self,
        client: AsyncClient,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        created = (
            await client.post(
                "/members",
                json={
                    "name": "Name",
                    "email": "test@example.com",
                    "password": "password",
                },
            )
        ).json()
        member_id = created["id"]
        assert created["is_verified"] is False

        token = verification_token_issuer.issue(member_id)
        response = await client.post(
            "/members/verify", json={"token": token}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == member_id
        assert body["is_verified"] is True

    async def test_verify_is_idempotent(
        self,
        client: AsyncClient,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        created = (
            await client.post(
                "/members",
                json={
                    "name": "Name",
                    "email": "test@example.com",
                    "password": "password",
                },
            )
        ).json()
        token = verification_token_issuer.issue(created["id"])

        first = await client.post("/members/verify", json={"token": token})
        second = await client.post("/members/verify", json={"token": token})

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["is_verified"] is True

    async def test_verify_with_garbage_token_returns_401(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/members/verify", json={"token": "not-a-jwt"}
        )
        assert response.status_code == 401

    async def test_verify_with_access_token_returns_401(
        self,
        client: AsyncClient,
        token_issuer: TokenIssuer,
    ):
        # Access tokens carry no `purpose=verify_email` claim and must not
        # be accepted by the verify endpoint.
        access = token_issuer.issue_access_token(uuid4())
        response = await client.post(
            "/members/verify", json={"token": access}
        )
        assert response.status_code == 401

    async def test_verify_with_token_for_unknown_member_returns_404(
        self,
        client: AsyncClient,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        ghost_token = verification_token_issuer.issue(uuid4())
        response = await client.post(
            "/members/verify", json={"token": ghost_token}
        )
        assert response.status_code == 404

    async def test_verify_empty_token_returns_422(self, client: AsyncClient):
        response = await client.post("/members/verify", json={"token": ""})
        assert response.status_code == 422
