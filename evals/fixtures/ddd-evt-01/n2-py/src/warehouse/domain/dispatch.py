from collections import defaultdict
from typing import Callable

from warehouse.domain.events import IntegrationEvent, ReservationMade


class EventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def dispatch(self, event: IntegrationEvent) -> None:
        for handler in self._handlers[type(event)]:
            handler(event)


class ReservationEventHandler:
    def __call__(self, event: ReservationMade) -> None:
        print(f"reserved by {event.reserved_by}")
