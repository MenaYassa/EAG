"""In-process event bus for EAG."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from eag.events.event import Event

EventT = TypeVar("EventT", bound=Event)
EventHandler = Callable[[EventT], None]


class Subscription:
    """Represents an active subscription to an event type."""

    def __init__(
        self,
        sub_id: UUID,
        event_type: type[Event],
        callback: Callable[[Event], None],
        event_bus: EventBus,
    ) -> None:
        self._id = sub_id
        self._event_type = event_type
        self._callback = callback
        self._event_bus = event_bus
        self._active = True

    @property
    def id(self) -> UUID:
        """Return the subscription ID."""
        return self._id

    @property
    def event_type(self) -> type[Event]:
        """Return the event type."""
        return self._event_type

    @property
    def callback(self) -> Callable[[Event], None]:
        """Return the callback function."""
        return self._callback

    @property
    def active(self) -> bool:
        """Return True if the subscription is active."""
        return self._active

    def unsubscribe(self) -> None:
        """Unsubscribe this subscription from the event bus."""
        if self._active:
            self._event_bus._remove_subscription(self)
            self._active = False

    def __enter__(self) -> Subscription:
        return self

    def __exit__(self, *args: Any) -> None:
        self.unsubscribe()


class EventBus:
    """Publish domain events to registered subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[
            type[Event],
            dict[UUID, Subscription],
        ] = defaultdict(dict)

    def subscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> Subscription:
        """Subscribe a handler to an event type and return a Subscription."""
        erased_handler = cast(
            Callable[[Event], None],
            cast(Any, handler),
        )

        sub_id = uuid4()
        sub = Subscription(sub_id, event_type, erased_handler, self)
        self._subscribers[event_type][sub_id] = sub
        return sub

    def unsubscribe(
        self,
        target: type[EventT] | Subscription,
        handler: EventHandler[EventT] | None = None,
    ) -> None:
        """Unsubscribe a handler or Subscription from the event bus."""
        if isinstance(target, Subscription):
            target.unsubscribe()
            return

        event_type = target
        if handler is None:
            return

        erased_handler = cast(
            Callable[[Event], None],
            cast(Any, handler),
        )

        subs = self._subscribers.get(event_type, {})
        for sub in list(subs.values()):
            if sub.callback == erased_handler:
                sub.unsubscribe()
                break

    def _remove_subscription(self, sub: Subscription) -> None:
        """Internal method to remove a subscription."""
        handlers = self._subscribers.get(sub.event_type)
        if handlers and sub.id in handlers:
            del handlers[sub.id]
            if not handlers:
                self._subscribers.pop(sub.event_type, None)

    def publish(self, event: Event) -> None:
        """Publish an event to its registered subscribers."""
        subs = self._subscribers.get(type(event), {})
        # Iterate over a copy of values to allow unsubscription during iteration
        for sub in tuple(subs.values()):
            if sub.active:
                sub.callback(event)

    def subscriber_count(
        self,
        event_type: type[Event],
    ) -> int:
        """Return the number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, {}))

    def clear(self) -> None:
        """Remove all subscribers."""
        self._subscribers.clear()