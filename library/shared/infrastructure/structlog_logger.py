import structlog

from library.shared.application import Logger


def get_logger(name: str) -> Logger:
    """Return a structlog-backed Logger.

    structlog's BoundLogger structurally satisfies the Logger protocol —
    no wrapper class needed. Configuration (JSON vs console, log level,
    bound contextvars) is handled centrally in
    `library.shared.logging_config.configure_logging` and the HTTP
    middleware.
    """
    return structlog.get_logger(name)
