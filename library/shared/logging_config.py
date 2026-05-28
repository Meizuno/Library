import logging
import sys

import structlog

from library.shared.config import LogLevel


def configure_logging(
    json_format: bool = False, log_level: LogLevel = "INFO"
) -> None:
    """Configure structlog and bridge stdlib logging through the same pipeline.

    json_format=True emits one JSON object per line (production).
    json_format=False emits human-readable colored output (development).
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json_format
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    # Logger.setLevel accepts the level name as a string directly; this avoids
    # the deprecated `logging.getLevelName(str) -> int` lookup. Settings has
    # already validated log_level is one of DEBUG/INFO/WARNING/ERROR/CRITICAL.
    root_logger.setLevel(log_level)
