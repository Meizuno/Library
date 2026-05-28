from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class RefreshToken:
    id: UUID = field(init=False, default_factory=uuid4)
    member_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self):
        if not self.token_hash:
            raise ValueError("token_hash cannot be empty")

    def __eq__(self, other):
        if not isinstance(other, RefreshToken):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def revoke(self, at: datetime) -> None:
        if self.revoked_at is None:
            self.revoked_at = at
