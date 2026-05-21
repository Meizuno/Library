from uuid import UUID

from library.domain import (
    Book,
    Member,
    Loan,
    ISBN,
    Email,
    BookNotFound,
    MemberNotFound,
    LoanNotFound,
)


class InMemoryBookRepository:
    def __init__(self):
        self._book_db: dict[UUID, Book] = {}

    async def save(self, book: Book) -> None:
        self._book_db[book.id] = book

    async def find_by_id(self, book_id: UUID) -> Book | None:
        return self._book_db.get(book_id)

    async def find_by_isbn(self, isbn: ISBN) -> Book | None:
        for book in self._book_db.values():
            if book.isbn == isbn:
                return book
        return None

    async def list_all(self) -> list[Book]:
        return list(self._book_db.values())

    async def delete(self, book_id: UUID) -> None:
        if book_id not in self._book_db:
            raise BookNotFound(f"Book {book_id} not found")

        del self._book_db[book_id]


class InMemoryMemberRepository:
    def __init__(self):
        self._member_db: dict[UUID, Member] = {}

    async def save(self, member: Member) -> None:
        self._member_db[member.id] = member

    async def find_by_id(self, member_id: UUID) -> Member | None:
        return self._member_db.get(member_id)

    async def find_by_email(self, email: Email) -> Member | None:
        for member in self._member_db.values():
            if member.email == email:
                return member
        return None

    async def list_all(self) -> list[Member]:
        return list(self._member_db.values())

    async def delete(self, member_id: UUID) -> None:
        if member_id not in self._member_db:
            raise MemberNotFound(f"Member {member_id} not found")

        del self._member_db[member_id]


class InMemoryLoanRepository:
    def __init__(self):
        self._loan_db: dict[UUID, Loan] = {}

    async def save(self, loan: Loan) -> None:
        self._loan_db[loan.id] = loan

    async def find_by_id(self, loan_id: UUID) -> Loan | None:
        return self._loan_db.get(loan_id)

    async def find_active_by_book(self, book_id: UUID) -> Loan | None:
        for loan in self._loan_db.values():
            if loan.book_id == book_id and not loan.is_returned:
                return loan
        return None

    async def find_by_member(self, member_id: UUID) -> list[Loan]:
        return [
            loan
            for loan in self._loan_db.values()
            if loan.member_id == member_id
        ]

    async def list_all(self) -> list[Loan]:
        return list(self._loan_db.values())

    async def delete(self, loan_id: UUID) -> None:
        if loan_id not in self._loan_db:
            raise LoanNotFound(f"Loan {loan_id} not found")

        del self._loan_db[loan_id]
