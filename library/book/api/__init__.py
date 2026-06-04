from fastapi import APIRouter

from library.book.api.routes import (
    add_book,
    delete_book,
    list_books,
    read_book,
    update_book,
)

# Each route module owns its own APIRouter with the full prefix and tags;
# this aggregator just stitches them together so main.py imports one symbol.
router = APIRouter()
router.include_router(list_books.router)
router.include_router(add_book.router)
router.include_router(read_book.router)
router.include_router(update_book.router)
router.include_router(delete_book.router)
