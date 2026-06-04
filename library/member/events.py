from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MemberRegistered:
    """Emitted by AddMemberUseCase once a new member has been persisted.

    Carries the FACTS about the registration — id, name, email — and
    nothing about how downstream subscribers will react to them. In
    particular, no verification token or email body: subscribers that
    need a token issue their own via VerificationTokenIssuer. Keeping
    the event side-effect-free is what makes the bus pluggable
    (multiple subscribers can react without coordinating on payload).
    """

    member_id: UUID
    name: str
    email: str
