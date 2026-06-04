import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

from library.shared.adapters import get_logger

logger = get_logger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Bind request_id + log request start/finish.

    Any log call within the request (including from RedisCache, repositories, etc.)
    automatically includes request_id thanks to structlog contextvars.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=str(uuid.uuid4()),
        method=request.method,
        path=request.url.path,
    )

    logger.info("request_started")
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed")
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request_finished",
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response
