from passlib.context import CryptContext


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["argon2"], deprecated="auto")

    def hash(self, password: str) -> str:
        return self._ctx.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._ctx.verify(password, hashed)
        except ValueError:
            return False
