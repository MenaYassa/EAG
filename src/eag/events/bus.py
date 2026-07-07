"""In-process event bus for EAG."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar, cast

from eag.events.event import Event

EventT = TypeVar("EventT", bound=Event)
EventHandler = Callable[[EventT], None]


class EventBus:
    """Publish domain events to registered subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[
            type[Event],
            list[Callable[[Event], None]],
        ] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        """Subscribe a handler to an event type."""
        handlers = self._subscribers[event_type]

        erased_handler = cast(
            Callable[[Event], None],
            cast(Any, handler),
        )

        if erased_handler not in handlers:
            handlers.append(erased_handler)

    def unsubscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        """Unsubscribe a handler from an event type."""
        handlers = self._subscribers.get(event_type)

        if not handlers:
            return

        erased_handler = cast(
            Callable[[Event], None],
            cast(Any, handler),
        )

        if erased_handler in handlers:
            handlers.remove(erased_handler)

        if not handlers:
            self._subscribers.pop(event_type, None)

    def publish(self, event: Event) -> None:
        """Publish an event to its registered subscribers."""
        handlers = tuple(self._subscribers.get(type(event), ()))

        for handler in handlers:
            handler(event)

    def subscriber_count(
        self,
        event_type: type[Event],
    ) -> int:
        """Return the number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, ()))

    def clear(self) -> None:
        """Remove all subscribers."""
        self._subscribers.clear()
