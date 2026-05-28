from datetime import datetime

from library.shared.application import Clock
from library.shared.infrastructure import SystemClock


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
