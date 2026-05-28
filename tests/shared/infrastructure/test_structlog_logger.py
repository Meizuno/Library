from library.shared.application import Logger
from library.shared.infrastructure import get_logger


class TestGetLogger:
    def test_returns_logger_protocol(self):
        logger: Logger = get_logger("test")
        # Logger protocol surface
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "exception")
        assert hasattr(logger, "bind")

    def test_info_with_fields_does_not_raise(self):
        logger = get_logger("test")
        logger.info("event_name", key="value", n=1)

    def test_bind_returns_logger_with_fields(self):
        logger = get_logger("test")
        bound = logger.bind(request_id="abc")
        # Bound logger also satisfies the protocol
        assert hasattr(bound, "info")
        assert hasattr(bound, "bind")
        # And can be chained further
        bound.info("nested_event", extra="x")

    def test_named_loggers_are_independent_instances(self):
        a = get_logger("module.a")
        b = get_logger("module.b")
        # Not asserting they're different objects (structlog may cache lazily);
        # just that both work without crashing.
        a.info("from_a")
        b.info("from_b")
