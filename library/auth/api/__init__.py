from fastapi import APIRouter

from library.auth.api.routes import login, logout, refresh

# Each route module owns its own APIRouter with the full prefix and tags;
# this aggregator just stitches them together so main.py imports one symbol.
router = APIRouter()
router.include_router(login.router)
router.include_router(refresh.router)
router.include_router(logout.router)
