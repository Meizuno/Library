from dataclasses import dataclass


@dataclass(frozen=True)
class AddBookCommand:
    title: str
    author: str
    isbn: str
