from fastapi import APIRouter

from library.member.api.routes import (
    add_member,
    delete_member,
    list_members,
    read_member,
    verify_member,
)

# Each route module owns its own APIRouter with the full prefix and tags;
# this aggregator just stitches them together so main.py imports one symbol.
router = APIRouter()
router.include_router(list_members.router)
router.include_router(add_member.router)
router.include_router(verify_member.router)
router.include_router(read_member.router)
router.include_router(delete_member.router)
