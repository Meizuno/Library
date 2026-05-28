from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from library.book.application import BookAlreadyExists
from library.book.domain import BookNotAvailable, BookNotFound
from library.book.presentation.api.router import router as book_router
from library.loan.domain import LoanNotFound
from library.loan.presentation.api.router import router as loan_router
from library.member.application import MemberAlreadyExists
from library.member.domain import MemberNotFound
from library.member.presentation.api.router import router as member_router
from library.shared.infrastructure import metadata
from library.shared.logging_config import configure_logging
from library.shared.presentation.api.dependencies import get_settings
from library.shared.presentation.api.middleware import (
    request_logging_middleware,
)


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


@app.get("/health")
def health_check():
    return "OK"
