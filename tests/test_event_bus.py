"""Tests for the EventBus v2 subscription lifecycle."""

from dataclasses import dataclass

from eag.events import Event
from eag.events.bus import EventBus, Subscription


@dataclass(frozen=True, slots=True, kw_only=True)
class DummyEvent(Event):
    """Dummy event for testing."""

    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OtherEvent(Event):
    """Another dummy event."""

    value: str


class TestEventBusSubscriptions:
    def test_subscribe_returns_subscription(self) -> None:
        bus = EventBus()
        sub = bus.subscribe(DummyEvent, lambda e: None)
        assert isinstance(sub, Subscription)
        assert sub.active is True
        assert bus.subscriber_count(DummyEvent) == 1

    def test_unsubscribe_via_subscription_object(self) -> None:
        bus = EventBus()
        received: list[int] = []
        sub = bus.subscribe(DummyEvent, lambda e: received.append(e.value))

        bus.publish(DummyEvent(value=1))
        assert received == [1]

        sub.unsubscribe()
        assert sub.active is False
        assert bus.subscriber_count(DummyEvent) == 0

        bus.publish(DummyEvent(value=2))
        assert received == [1]  # No new events received

    def test_unsubscribe_via_event_bus(self) -> None:
        bus = EventBus()
        received: list[int] = []
        sub = bus.subscribe(DummyEvent, lambda e: received.append(e.value))

        bus.unsubscribe(sub)
        assert sub.active is False
        assert bus.subscriber_count(DummyEvent) == 0

    def test_unsubscribe_idempotent(self) -> None:
        bus = EventBus()
        sub = bus.subscribe(DummyEvent, lambda e: None)

        sub.unsubscribe()
        sub.unsubscribe()  # Should not raise
        bus.unsubscribe(sub)  # Should not raise

    def test_multiple_subscriptions(self) -> None:
        bus = EventBus()
        received1: list[int] = []
        received2: list[int] = []

        sub1 = bus.subscribe(DummyEvent, lambda e: received1.append(e.value))
        bus.subscribe(DummyEvent, lambda e: received2.append(e.value))

        bus.publish(DummyEvent(value=1))

        assert received1 == [1]
        assert received2 == [1]

        sub1.unsubscribe()
        bus.publish(DummyEvent(value=2))

        assert received1 == [1]
        assert received2 == [1, 2]

    def test_unsubscribe_during_publish(self) -> None:
        """Ensure unsubscribing during publish doesn't break iteration."""
        bus = EventBus()
        received: list[int] = []

        def handler(e: DummyEvent) -> None:
            received.append(e.value)
            if e.value == 1:
                sub.unsubscribe()

        sub = bus.subscribe(DummyEvent, handler)

        bus.publish(DummyEvent(value=1))
        bus.publish(DummyEvent(value=2))

        assert received == [1]
        assert sub.active is False

    def test_context_manager_support(self) -> None:
        bus = EventBus()
        received: list[int] = []

        with bus.subscribe(DummyEvent, lambda e: received.append(e.value)) as sub:
            assert sub.active is True
            bus.publish(DummyEvent(value=1))
            assert received == [1]

        assert sub.active is False
        bus.publish(DummyEvent(value=2))
        assert received == [1]

    def test_backward_compatible_unsubscribe(self) -> None:
        """Ensure unsubscribe with (event_type, handler) still works."""
        bus = EventBus()
        received: list[int] = []

        def handler(e: DummyEvent) -> None:
            received.append(e.value)

        bus.subscribe(DummyEvent, handler)
        assert bus.subscriber_count(DummyEvent) == 1

        bus.publish(DummyEvent(value=1))
        assert received == [1]

        bus.unsubscribe(DummyEvent, handler)
        assert bus.subscriber_count(DummyEvent) == 0

        bus.publish(DummyEvent(value=2))
        assert received == [1]

    def test_clear_removes_all_subscriptions(self) -> None:
        bus = EventBus()
        bus.subscribe(DummyEvent, lambda e: None)
        bus.subscribe(OtherEvent, lambda e: None)

        assert bus.subscriber_count(DummyEvent) == 1
        assert bus.subscriber_count(OtherEvent) == 1

        bus.clear()

        assert bus.subscriber_count(DummyEvent) == 0
        assert bus.subscriber_count(OtherEvent) == 0
