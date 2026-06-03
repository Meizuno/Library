from uuid import UUID, uuid4

import pytest

from library.member.models import Email, Member, Password


_HASH = "hashed:password"


class TestEmail:
    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "first.last@example.com",
            "user@mail.example.co.uk",
            "user123@example.com",
        ],
    )
    def test_valid_email(self, email: str):
        valid_email = Email(email)
        assert valid_email.value == email

    @pytest.mark.parametrize(
        "email",
        [
            "",
            "no-at-sign",
            "@example.com",
            "user@",
            "user@example",
            " ",
            "a@b@c.com",
        ],
    )
    def test_invalid_email(self, email: str):
        with pytest.raises(ValueError, match=f"invalid email: {email!r}"):
            _ = Email(email)


class TestPassword:
    def test_valid_password(self):
        pw = Password("correcthorse")
        assert pw.value == "correcthorse"

    def test_exactly_min_length_is_valid(self):
        pw = Password("a" * Password.MIN_LENGTH)
        assert pw.value == "a" * Password.MIN_LENGTH

    @pytest.mark.parametrize("plain", ["", "short", "1234567"])
    def test_too_short_raises(self, plain: str):
        with pytest.raises(ValueError, match="password must be at least"):
            _ = Password(plain)

    def test_str_does_not_leak_value(self):
        pw = Password("correcthorse")
        assert "correcthorse" not in str(pw)
        assert str(pw) == "***"

    def test_password_is_frozen(self):
        pw = Password("correcthorse")
        with pytest.raises(Exception):
            pw.value = "other"  # type: ignore[misc]


class TestMember:
    def test_valid_member(self, valid_email: Email):
        member = Member(name="Name", email=valid_email, password_hash=_HASH)

        assert isinstance(member.id, UUID)
        assert member.name == "Name"
        assert member.email == valid_email
        assert member.email.value == valid_email.value
        assert member.password_hash == _HASH

    def test_each_member_has_unique_id(self, valid_email):
        member_1 = Member(name="A", email=valid_email, password_hash=_HASH)
        member_2 = Member(name="B", email=valid_email, password_hash=_HASH)
        assert member_1.id != member_2.id

    def test_member_id_can_be_set_after_construction(self, valid_email):
        custom_id = uuid4()
        member = Member(name="X", email=valid_email, password_hash=_HASH)
        member.id = custom_id
        assert member.id == custom_id

    def test_id_is_not_settable_via_constructor(self, valid_email):
        with pytest.raises(TypeError):
            Member(  # pylint: disable=unexpected-keyword-arg
                id=uuid4(),
                name="Name",
                email=valid_email,
                password_hash=_HASH,
            )

    @pytest.mark.parametrize("name", ["", " "])
    def test_empty_name(self, name, valid_email):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Member(name=name, email=valid_email, password_hash=_HASH)

    def test_empty_password_hash_raises(self, valid_email):
        with pytest.raises(ValueError, match="password_hash cannot be empty"):
            Member(name="Name", email=valid_email, password_hash="")

    def test_member_is_hashable(self, valid_email):
        """__hash__ працює — Member можна покласти в set/dict."""
        member = Member(name="X", email=valid_email, password_hash=_HASH)
        s = {member}
        assert member in s

    def test_members_with_same_id_share_hash(self, valid_email):
        """Два Member з однаковим id мають однаковий hash."""
        shared_id = uuid4()
        m_1 = Member(name="A", email=valid_email, password_hash=_HASH)
        m_2 = Member(name="B", email=valid_email, password_hash=_HASH)
        m_1.id = shared_id
        m_2.id = shared_id
        assert hash(m_1) == hash(m_2)
        assert len({m_1, m_2}) == 1

    def test_is_verified_defaults_to_false(self, valid_email):
        member = Member(name="Name", email=valid_email, password_hash=_HASH)
        assert member.is_verified is False

    def test_is_verified_can_be_set_via_constructor(self, valid_email):
        member = Member(
            name="Name",
            email=valid_email,
            password_hash=_HASH,
            is_verified=True,
        )
        assert member.is_verified is True

    def test_mark_verified_flips_to_true(self, valid_email):
        member = Member(name="Name", email=valid_email, password_hash=_HASH)
        member.mark_verified()
        assert member.is_verified is True

    def test_mark_verified_is_idempotent(self, valid_email):
        member = Member(
            name="Name",
            email=valid_email,
            password_hash=_HASH,
            is_verified=True,
        )
        member.mark_verified()  # no-op
        assert member.is_verified is True
