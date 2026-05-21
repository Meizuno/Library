from datetime import datetime

from library.application import Clock
from library.infrastructure import SystemClock


class TestSystemClock:
    def test_satisfies_clock_protocol(self):
        clock: Clock = SystemClock()
        assert hasattr(clock, "now")

    def test_now_returns_datetime_within_window(self):
        before = datetime.now()
        result = SystemClock().now()
        after = datetime.now()

        assert isinstance(result, datetime)
        assert before <= result <= after
