from library.shared.infrastructure import Argon2PasswordHasher


class TestArgon2PasswordHasher:
    def test_hash_then_verify_returns_true(self):
        hasher = Argon2PasswordHasher()
        hashed = hasher.hash("correct horse battery staple")
        assert hasher.verify("correct horse battery staple", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hasher = Argon2PasswordHasher()
        hashed = hasher.hash("correct password")
        assert hasher.verify("wrong password", hashed) is False

    def test_verify_malformed_hash_returns_false(self):
        hasher = Argon2PasswordHasher()
        assert hasher.verify("password", "not-an-argon2-hash") is False

    def test_hash_output_is_argon2_format(self):
        hasher = Argon2PasswordHasher()
        # argon2-cffi default is argon2id; encoded hashes start with $argon2id$
        hashed = hasher.hash("password")
        assert hashed.startswith("$argon2")

    def test_hash_is_salted(self):
        """Same password hashed twice produces different output (per-hash salt)."""
        hasher = Argon2PasswordHasher()
        a = hasher.hash("password")
        b = hasher.hash("password")
        assert a != b
        # But both verify against the same input
        assert hasher.verify("password", a)
        assert hasher.verify("password", b)
