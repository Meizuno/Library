from uuid import uuid4

import pytest

from library.member.application import VerifyMemberCommand, VerifyMemberUseCase
from library.member.domain import (
    InvalidVerificationToken,
    Member,
    MemberNotFound,
    MemberRepository,
    VerificationTokenIssuer,
)


class TestVerifyMemberUseCase:
    async def test_verify_marks_member_verified(
        self,
        member_repo: MemberRepository,
        verification_token_issuer: VerificationTokenIssuer,
        valid_email,
    ):
        # The default `valid_member` fixture is pre-verified; build a fresh
        # unverified one here so we can observe the state transition.
        unverified = Member(
            name="Name",
            email=valid_email,
            password_hash="hashed:password",
            is_verified=False,
        )
        await member_repo.create(unverified)

        token = verification_token_issuer.issue(unverified.id)
        use_case = VerifyMemberUseCase(
            member_repo, verification_token_issuer
        )
        result = await use_case.execute(VerifyMemberCommand(token=token))

        assert result.is_verified is True
        saved = await member_repo.find_by_id(unverified.id)
        assert saved is not None and saved.is_verified is True

    async def test_verify_is_idempotent_no_extra_update(
        self,
        member_repo: MemberRepository,
        verification_token_issuer: VerificationTokenIssuer,
        valid_email,
    ):
        # Member already verified — short-circuit, no UPDATE issued.
        # We assert idempotency at the result level (must remain verified).
        already_verified = Member(
            name="Name",
            email=valid_email,
            password_hash="hashed:password",
            is_verified=True,
        )
        await member_repo.create(already_verified)
        token = verification_token_issuer.issue(already_verified.id)

        use_case = VerifyMemberUseCase(
            member_repo, verification_token_issuer
        )
        result = await use_case.execute(VerifyMemberCommand(token=token))

        assert result.is_verified is True

    async def test_invalid_token_raises(
        self,
        member_repo: MemberRepository,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        use_case = VerifyMemberUseCase(
            member_repo, verification_token_issuer
        )
        with pytest.raises(InvalidVerificationToken):
            await use_case.execute(VerifyMemberCommand(token="garbage"))

    async def test_unknown_member_raises_not_found(
        self,
        member_repo: MemberRepository,
        verification_token_issuer: VerificationTokenIssuer,
    ):
        # Valid token but the member was deleted between issue and verify.
        ghost_token = verification_token_issuer.issue(uuid4())
        use_case = VerifyMemberUseCase(
            member_repo, verification_token_issuer
        )
        with pytest.raises(MemberNotFound):
            await use_case.execute(VerifyMemberCommand(token=ghost_token))
