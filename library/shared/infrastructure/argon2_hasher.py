from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import Argon2Error, InvalidHashError


class Argon2PasswordHasher:
    """argon2-cffi adapter for the PasswordHasher port.

    Uses argon2-cffi directly rather than passlib (which depends on the
    removed-in-3.13 `crypt` stdlib module). Argon2id is the default and
    is the current OWASP recommendation for password hashing.

    Note: argon2-cffi's verify(hash, password) takes its arguments in the
    opposite order from this adapter's verify(password, hash). The wrapper
    swaps them so the port stays consistent across implementations.

    Both Argon2Error (wrong password, corrupted hash) and InvalidHashError
    (malformed input) are caught — argon2-cffi quirk: InvalidHashError does
    NOT inherit from Argon2Error, it's a direct subclass of Exception.
    """

    def __init__(self) -> None:
        self._hasher = _Argon2()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except (Argon2Error, InvalidHashError):
            return False
