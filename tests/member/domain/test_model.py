from uuid import UUID, uuid4

import pytest

from library.member.domain import Email, Member


class TestMember:
    def test_valid_member(self, valid_email: Email):
        member = Member(name="Name", email=valid_email)

        assert isinstance(member.id, UUID)
        assert member.name == "Name"
        assert member.email == valid_email
        assert member.email.value == valid_email.value

    def test_each_member_has_unique_id(self, valid_email):
        member_1 = Member(name="A", email=valid_email)
        member_2 = Member(name="B", email=valid_email)
        assert member_1.id != member_2.id

    def test_member_id_can_be_set_after_construction(self, valid_email):
        custom_id = uuid4()
        member = Member(name="X", email=valid_email)
        member.id = custom_id
        assert member.id == custom_id

    def test_id_is_not_settable_via_constructor(self, valid_email):
        with pytest.raises(TypeError):
            Member(  # pylint: disable=unexpected-keyword-arg
                id=uuid4(),
                name="Name",
                email=valid_email,
            )

    @pytest.mark.parametrize("name", ["", " "])
    def test_empty_name(self, name, valid_email):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Member(name=name, email=valid_email)

    def test_member_is_hashable(self, valid_email):
        """__hash__ працює — Member можна покласти в set/dict."""
        member = Member(name="X", email=valid_email)
        s = {member}
        assert member in s

    def test_members_with_same_id_share_hash(self, valid_email):
        """Два Member з однаковим id мають однаковий hash."""
        shared_id = uuid4()
        m_1 = Member(name="A", email=valid_email)
        m_2 = Member(name="B", email=valid_email)
        m_1.id = shared_id
        m_2.id = shared_id
        assert hash(m_1) == hash(m_2)
        assert len({m_1, m_2}) == 1
