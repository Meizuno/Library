from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from library.auth.api import router as auth_router
from library.auth.exceptions import (
    InvalidCredentials,
    RefreshTokenExpired,
    RefreshTokenInvalid,
    RefreshTokenRevoked,
)
from library.book.api import router as book_router
from library.book.exceptions import (
    BookAlreadyExists,
    BookNotAvailable,
    BookNotFound,
)
from library.loan.api import router as loan_router
from library.loan.exceptions import LoanNotFound
from library.member.api import router as member_router
from library.member.exceptions import (
    InvalidVerificationToken,
    MemberAlreadyExists,
    MemberNotFound,
    MemberNotVerified,
)
from library.shared.adapters import metadata
from library.shared.api.dependencies import get_settings
from library.shared.api.middleware import request_logging_middleware
from library.shared.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(
        json_format=settings.log_format == "json",
        log_level=settings.log_level,
    )
    app.state.engine = create_async_engine(settings.database_url)
    app.state.redis = Redis.from_url(settings.redis_url)
    async with app.state.engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    yield

    await app.state.redis.aclose()
    await app.state.engine.dispose()


app = FastAPI(lifespan=lifespan)
app.middleware("http")(request_logging_middleware)
app.include_router(auth_router)
app.include_router(book_router)
app.include_router(member_router)
app.include_router(loan_router)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"message": str(exc)})


@app.exception_handler(BookAlreadyExists)
async def book_duplicate_exception_handler(_: Request, exc: BookAlreadyExists):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(BookNotFound)
async def book_not_found_handler(_: Request, exc: BookNotFound):
    return JSONResponse(status_code=404, content={"message": str(exc)})


@app.exception_handler(MemberAlreadyExists)
async def member_duplicate_exception_handler(
    _: Request, exc: MemberAlreadyExists
):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(MemberNotFound)
async def member_not_found_handler(_: Request, exc: MemberNotFound):
    return JSONResponse(status_code=404, content={"message": str(exc)})


@app.exception_handler(BookNotAvailable)
async def book_not_available_handler(_: Request, exc: BookNotAvailable):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(LoanNotFound)
async def loan_not_found_handler(_: Request, exc: LoanNotFound):
    return JSONResponse(status_code=404, content={"message": str(exc)})


@app.exception_handler(InvalidCredentials)
async def invalid_credentials_handler(_: Request, exc: InvalidCredentials):
    return JSONResponse(status_code=401, content={"message": str(exc)})


@app.exception_handler(RefreshTokenInvalid)
async def refresh_token_invalid_handler(_: Request, exc: RefreshTokenInvalid):
    return JSONResponse(status_code=401, content={"message": str(exc)})


@app.exception_handler(RefreshTokenExpired)
async def refresh_token_expired_handler(_: Request, exc: RefreshTokenExpired):
    return JSONResponse(status_code=401, content={"message": str(exc)})


@app.exception_handler(RefreshTokenRevoked)
async def refresh_token_revoked_handler(_: Request, exc: RefreshTokenRevoked):
    return JSONResponse(status_code=401, content={"message": str(exc)})


@app.exception_handler(InvalidVerificationToken)
async def invalid_verification_token_handler(
    _: Request, exc: InvalidVerificationToken
):
    return JSONResponse(status_code=401, content={"message": str(exc)})


@app.exception_handler(MemberNotVerified)
async def member_not_verified_handler(_: Request, exc: MemberNotVerified):
    return JSONResponse(status_code=403, content={"message": str(exc)})


@app.get("/health")
def health_check():
    return "OK"
