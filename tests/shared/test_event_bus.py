from dataclasses import dataclass

from library.shared.adapters import InProcessEventBus


@dataclass(frozen=True)
class _Pinged:
    value: int


@dataclass(frozen=True)
class _Pongued:
    value: int


class TestInProcessEventBus:
    async def test_publishes_to_one_subscriber(self):
        bus = InProcessEventBus()
        received: list[_Pinged] = []

        async def handler(event: _Pinged) -> None:
            received.append(event)

        bus.subscribe(_Pinged, handler)

        await bus.publish(_Pinged(value=1))

        assert received == [_Pinged(value=1)]

    async def test_fan_out_to_multiple_subscribers(self):
        # Two handlers registered for the same event type both fire.
        bus = InProcessEventBus()
        a: list[_Pinged] = []
        b: list[_Pinged] = []

        async def handler_a(event: _Pinged) -> None:
            a.append(event)

        async def handler_b(event: _Pinged) -> None:
            b.append(event)

        bus.subscribe(_Pinged, handler_a)
        bus.subscribe(_Pinged, handler_b)

        await bus.publish(_Pinged(value=42))

        assert a == [_Pinged(value=42)]
        assert b == [_Pinged(value=42)]

    async def test_dispatch_is_keyed_on_concrete_type(self):
        # Handler subscribed to _Pinged must not receive _Pongued.
        bus = InProcessEventBus()
        pinged: list[_Pinged] = []

        async def handler(event: _Pinged) -> None:
            pinged.append(event)

        bus.subscribe(_Pinged, handler)

        await bus.publish(_Pongued(value=99))

        assert pinged == []

    async def test_no_subscribers_is_noop(self):
        # Publishing to an unsubscribed event type must not raise.
        bus = InProcessEventBus()
        await bus.publish(_Pinged(value=0))

    async def test_handler_exception_is_swallowed(self):
        # A failing handler must not propagate — that's the whole point
        # of the EDA decoupling: publisher's command succeeds even if a
        # subscriber's side-effect fails.
        bus = InProcessEventBus()

        async def boom(_: _Pinged) -> None:
            raise RuntimeError("subscriber explosion")

        bus.subscribe(_Pinged, boom)

        # Must not raise.
        await bus.publish(_Pinged(value=1))

    async def test_handler_exception_does_not_block_other_subscribers(
        self,
    ):
        # If handler A raises, handler B (registered after) still fires.
        bus = InProcessEventBus()
        survived: list[_Pinged] = []

        async def boom(_: _Pinged) -> None:
            raise RuntimeError("first handler down")

        async def survivor(event: _Pinged) -> None:
            survived.append(event)

        bus.subscribe(_Pinged, boom)
        bus.subscribe(_Pinged, survivor)

        await bus.publish(_Pinged(value=7))

        assert survived == [_Pinged(value=7)]

    async def test_subscribers_fire_in_registration_order(self):
        bus = InProcessEventBus()
        order: list[str] = []

        async def first(_: _Pinged) -> None:
            order.append("first")

        async def second(_: _Pinged) -> None:
            order.append("second")

        bus.subscribe(_Pinged, first)
        bus.subscribe(_Pinged, second)

        await bus.publish(_Pinged(value=0))

        assert order == ["first", "second"]
