"""Tests for the EAG event bus."""

from dataclasses import dataclass

from eag.events import Event, EventBus


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleEvent(Event):
    """Event used for event bus tests."""

    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OtherEvent(Event):
    """Second event used for isolation tests."""

    name: str


def test_subscriber_receives_event() -> None:
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(event: SampleEvent) -> None:
        received.append(event)

    bus.subscribe(SampleEvent, handler)

    event = SampleEvent(value=42)
    bus.publish(event)

    assert received == [event]


def test_unrelated_subscriber_does_not_receive_event() -> None:
    bus = EventBus()
    received: list[OtherEvent] = []

    def handler(event: OtherEvent) -> None:
        received.append(event)

    bus.subscribe(OtherEvent, handler)
    bus.publish(SampleEvent(value=42))

    assert received == []


def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(event: SampleEvent) -> None:
        received.append(event)

    bus.subscribe(SampleEvent, handler)
    bus.unsubscribe(SampleEvent, handler)
    bus.publish(SampleEvent(value=42))

    assert received == []


def test_duplicate_subscription_is_ignored() -> None:
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(event: SampleEvent) -> None:
        received.append(event)

    bus.subscribe(SampleEvent, handler)
    bus.subscribe(SampleEvent, handler)

    bus.publish(SampleEvent(value=42))

    assert len(received) == 1


def test_subscriber_count() -> None:
    bus = EventBus()

    def handler(event: SampleEvent) -> None:
        del event

    assert bus.subscriber_count(SampleEvent) == 0

    bus.subscribe(SampleEvent, handler)

    assert bus.subscriber_count(SampleEvent) == 1


def test_clear_removes_all_subscribers() -> None:
    bus = EventBus()

    def handler(event: SampleEvent) -> None:
        del event

    bus.subscribe(SampleEvent, handler)
    bus.clear()

    assert bus.subscriber_count(SampleEvent) == 0
