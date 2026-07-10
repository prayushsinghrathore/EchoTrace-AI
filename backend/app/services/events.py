"""
Internal event bus — publish/subscribe for async event dispatch.

Services publish events when state changes occur. Subscribers receive
events asynchronously for notification, activity tracking, WebSocket
broadcasting, and audit logging.
"""

from __future__ import annotations

import asyncio
import enum
import json
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EventPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class AppEvent:
    """A typed application event for the internal event bus."""

    def __init__(
        self,
        event_type: str,
        actor_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        data: dict[str, Any] | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.actor_id = str(actor_id) if actor_id else None
        self.workspace_id = str(workspace_id) if workspace_id else None
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.data = data or {}
        self.priority = priority
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "workspace_id": self.workspace_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "data": self.data,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


# Event type constants
EVENT_INVESTIGATION_CREATED = "investigation.created"
EVENT_INVESTIGATION_UPDATED = "investigation.updated"
EVENT_INVESTIGATION_CLOSED = "investigation.closed"
EVENT_EVIDENCE_CREATED = "evidence.created"
EVENT_EVIDENCE_UPLOADED = "evidence.uploaded"
EVENT_EVIDENCE_VERIFIED = "evidence.verified"
EVENT_EVIDENCE_DELETED = "evidence.deleted"
EVENT_ENTITY_APPROVED = "entity.approved"
EVENT_RELATIONSHIP_APPROVED = "relationship.approved"
EVENT_AI_JOB_COMPLETED = "ai.job_completed"
EVENT_REPORT_GENERATED = "report.generated"
EVENT_EXPORT_COMPLETED = "export.completed"
EVENT_NOTIFICATION_CREATED = "notification.created"
EVENT_COMMENT_ADDED = "comment.added"


class EventBus:
    """
    Internal async event bus with publish/subscribe.

    Thread-safe for a single event loop. Uses asyncio tasks for
    background dispatch so publishers are not blocked.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[AppEvent], Coroutine[Any, Any, None]]]] = {}
        self._wildcard_subscribers: list[Callable[[AppEvent], Coroutine[Any, Any, None]]] = []

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[AppEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe a handler to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Handler subscribed", event_type=event_type, handler=handler.__name__)

    def subscribe_all(self, handler: Callable[[AppEvent], Coroutine[Any, Any, None]]) -> None:
        """Subscribe a handler to ALL events (wildcard)."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[AppEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Unsubscribe a handler from a specific event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def publish(self, event: AppEvent) -> None:
        """Publish an event to all subscribers asynchronously."""
        __event_task = asyncio.create_task(self._dispatch(event))  # noqa: RUF006

    async def _dispatch(self, event: AppEvent) -> None:
        """Dispatch an event to all relevant subscribers."""
        handlers: list[Callable[[AppEvent], Coroutine[Any, Any, None]]] = []

        # Specific event type handlers
        if event.event_type in self._subscribers:
            handlers.extend(self._subscribers[event.event_type])

        # Wildcard handlers
        handlers.extend(self._wildcard_subscribers)

        if not handlers:
            return

        logger.debug("Dispatching event", event_type=event.event_type, handlers=len(handlers))

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error(
                    "Event handler failed",
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(exc),
                )

    @property
    def subscriber_count(self) -> int:
        return sum(len(v) for v in self._subscribers.values()) + len(self._wildcard_subscribers)


# Global event bus instance
event_bus = EventBus()
