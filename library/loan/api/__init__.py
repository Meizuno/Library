from fastapi import APIRouter, Depends

from library.auth.api.security import get_verified_member
from library.loan.api.routes import borrow_book, return_book

# /loans actions require BOTH a valid access token AND a verified
# member. The auth gate is declared once here at the aggregator level
# and applies to every route the child routers contribute.
router = APIRouter(dependencies=[Depends(get_verified_member)])
router.include_router(borrow_book.router)
router.include_router(return_book.router)
