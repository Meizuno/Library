from httpx import AsyncClient

from library.auth.presentation.api.security import (
    get_current_member,
    get_verified_member,
)
from library.shared.presentation.api.main import app


async def _register(client: AsyncClient, email: str = "user@example.com"):
    return await client.post(
        "/members",
        json={"name": "Name", "email": email, "password": "password"},
    )


class TestAuthAPI:
    async def test_login_returns_token_pair(self, client: AsyncClient):
        await _register(client)
        response = await client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "password"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient
    ):
        await _register(client)
        response = await client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "password"},
        )
        assert response.status_code == 401

    async def test_refresh_rotates_tokens(self, client: AsyncClient):
        await _register(client)
        login = (
            await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password"},
            )
        ).json()

        response = await client.post(
            "/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )

        assert response.status_code == 200
        new = response.json()
        assert new["refresh_token"] != login["refresh_token"]

    async def test_refresh_with_old_token_after_rotation_returns_401(
        self, client: AsyncClient
    ):
        await _register(client)
        login = (
            await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password"},
            )
        ).json()
        await client.post(
            "/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )

        replay = await client.post(
            "/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert replay.status_code == 401

    async def test_refresh_unknown_token_returns_401(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        assert response.status_code == 401

    async def test_logout_revokes_token(self, client: AsyncClient):
        await _register(client)
        login = (
            await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password"},
            )
        ).json()

        response = await client.post(
            "/auth/logout", json={"refresh_token": login["refresh_token"]}
        )
        assert response.status_code == 204

        # Subsequent refresh with the revoked token returns 401
        replay = await client.post(
            "/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert replay.status_code == 401


def _clear_auth_overrides() -> None:
    """Drop both auth-gate overrides so /loans/* uses real get_verified_member
    (which in turn invokes the real get_current_member)."""
    app.dependency_overrides.pop(get_current_member, None)
    app.dependency_overrides.pop(get_verified_member, None)


class TestProtectedLoanRoutes:
    """The /loans/* endpoints require a valid bearer token AND a verified
    member. The default `client` fixture auto-overrides both checks; we
    clear them here to exercise the real gate."""

    async def test_borrow_without_token_returns_401(
        self, client: AsyncClient
    ):
        _clear_auth_overrides()

        response = await client.post(
            "/loans",
            json={
                "book_id": "00000000-0000-0000-0000-000000000001",
                "member_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert response.status_code == 401

    async def test_borrow_with_invalid_token_returns_401(
        self, client: AsyncClient
    ):
        _clear_auth_overrides()

        response = await client.post(
            "/loans",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
            json={
                "book_id": "00000000-0000-0000-0000-000000000001",
                "member_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert response.status_code == 401

    async def test_return_without_token_returns_401(
        self, client: AsyncClient
    ):
        _clear_auth_overrides()

        response = await client.post(
            "/loans/00000000-0000-0000-0000-000000000001/return"
        )
        assert response.status_code == 401

    async def test_borrow_with_unverified_member_returns_403(
        self, client: AsyncClient, valid_member
    ):
        # An authenticated but unverified caller is rejected by the
        # `get_verified_member` gate. We keep the `get_current_member`
        # override (so auth succeeds) but drop the `get_verified_member`
        # override and flip the member's is_verified flag to False.
        valid_member.is_verified = False
        app.dependency_overrides.pop(get_verified_member, None)

        response = await client.post(
            "/loans",
            json={
                "book_id": "00000000-0000-0000-0000-000000000001",
                "member_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert response.status_code == 403
