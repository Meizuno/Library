from dataclasses import dataclass

from library.shared.adapters import InProcessEventBus


@dataclass(frozen=True)
class _Pinged:
    value: int


@dataclass(frozen=True)
class _Pongued:
    value: int


class _CollectPinged:
    """Test handler that records every _Pinged event it receives.

    Mirrors how production subscribers are shaped — a class with
    constructor state and a `handle(event)` method — so the bus
    contract is exercised the same way it is in main.py wiring.
    """

    def __init__(self) -> None:
        self.received: list[_Pinged] = []

    async def handle(self, event: _Pinged) -> None:
        self.received.append(event)


class _BoomPinged:
    async def handle(self, _: _Pinged) -> None:
        raise RuntimeError("subscriber explosion")


class TestInProcessEventBus:
    async def test_publishes_to_one_subscriber(self):
        bus = InProcessEventBus()
        handler = _CollectPinged()
        bus.subscribe(_Pinged, handler)

        await bus.publish(_Pinged(value=1))

        assert handler.received == [_Pinged(value=1)]

    async def test_fan_out_to_multiple_subscribers(self):
        # Two handlers registered for the same event type both fire.
        bus = InProcessEventBus()
        a = _CollectPinged()
        b = _CollectPinged()
        bus.subscribe(_Pinged, a)
        bus.subscribe(_Pinged, b)

        await bus.publish(_Pinged(value=42))

        assert a.received == [_Pinged(value=42)]
        assert b.received == [_Pinged(value=42)]

    async def test_dispatch_is_keyed_on_concrete_type(self):
        # Handler subscribed to _Pinged must not receive _Pongued.
        bus = InProcessEventBus()
        handler = _CollectPinged()
        bus.subscribe(_Pinged, handler)

        await bus.publish(_Pongued(value=99))

        assert handler.received == []

    async def test_no_subscribers_is_noop(self):
        # Publishing to an unsubscribed event type must not raise.
        bus = InProcessEventBus()
        await bus.publish(_Pinged(value=0))

    async def test_handler_exception_is_swallowed(self):
        # A failing handler must not propagate — that's the whole point
        # of the EDA decoupling: publisher's command succeeds even if a
        # subscriber's side-effect fails.
        bus = InProcessEventBus()
        bus.subscribe(_Pinged, _BoomPinged())

        # Must not raise.
        await bus.publish(_Pinged(value=1))

    async def test_handler_exception_does_not_block_other_subscribers(
        self,
    ):
        # If handler A raises, handler B (registered after) still fires.
        bus = InProcessEventBus()
        survivor = _CollectPinged()
        bus.subscribe(_Pinged, _BoomPinged())
        bus.subscribe(_Pinged, survivor)

        await bus.publish(_Pinged(value=7))

        assert survivor.received == [_Pinged(value=7)]

    async def test_subscribers_fire_in_registration_order(self):
        bus = InProcessEventBus()
        order: list[str] = []

        class _Recorder:
            def __init__(self, name: str) -> None:
                self._name = name

            async def handle(self, _: _Pinged) -> None:
                order.append(self._name)

        bus.subscribe(_Pinged, _Recorder("first"))
        bus.subscribe(_Pinged, _Recorder("second"))

        await bus.publish(_Pinged(value=0))

        assert order == ["first", "second"]
