from library.member.application.commands import VerifyMemberCommand
from library.member.domain import (
    Member,
    MemberNotFound,
    MemberRepository,
    VerificationTokenIssuer,
)


class VerifyMemberUseCase:
    """Decode a verification token and flip the member's `is_verified` flag.

    The `VerificationTokenIssuer` enforces the token's `purpose` claim, so
    an access token can't be substituted (and vice versa).

    Idempotent: if the member is already verified, the SQL UPDATE is
    skipped — both saving a write and signalling "this is fine, no change".
    """

    def __init__(
        self,
        member_repo: MemberRepository,
        verification_tokens: VerificationTokenIssuer,
    ):
        self._member_repo = member_repo
        self._verification_tokens = verification_tokens

    async def execute(self, command: VerifyMemberCommand) -> Member:
        member_id = self._verification_tokens.verify(command.token)
        member = await self._member_repo.find_by_id(member_id)
        if member is None:
            raise MemberNotFound(f"Member {member_id} not found")

        if member.is_verified:
            return member

        member.mark_verified()
        await self._member_repo.update(member)
        return member
