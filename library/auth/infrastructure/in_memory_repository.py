from uuid import UUID

from library.auth.domain import RefreshToken, RefreshTokenNotFound


class InMemoryRefreshTokenRepository:
    def __init__(self):
        self._tokens: dict[UUID, RefreshToken] = {}

    async def create(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token

    async def update(self, token: RefreshToken) -> None:
        if token.id not in self._tokens:
            raise RefreshTokenNotFound(f"RefreshToken {token.id} not found")
        self._tokens[token.id] = token

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        for token in self._tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    async def find_by_id(self, token_id: UUID) -> RefreshToken | None:
        return self._tokens.get(token_id)
