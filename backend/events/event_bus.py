"""Phase 6 async event bus (reuses the Phase 4 in-process bus).

Publishes domain events (``transaction.created``, ``financial_alert`` ...) to
SSE subscribers.  Agents may publish; the risk observer subscribes in-process.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.events.event_types import EVENT_FINANCIAL_ALERT
from backend.observers.event_bus import EventBus

# Re-export the low-level subscribe/unsubscribe/recent primitives.
subscribe = EventBus.subscribe
unsubscribe = EventBus.unsubscribe
recent = EventBus.recent
subscriber_count = EventBus.subscriber_count


async def publish(event_type: str, data: Dict[str, Any], severity: str = "INFO") -> Dict[str, Any]:
    """Publish an event asynchronously to the in-process bus."""
    return EventBus.publish(event_type, data, severity=severity)


async def publish_financial_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    return await publish(EVENT_FINANCIAL_ALERT, alert, severity=alert.get("severity", "INFO"))
