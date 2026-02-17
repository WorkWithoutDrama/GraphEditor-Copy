"""Job publisher adapter. In-memory stub; replace with Redis/SQS for production."""
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# In-memory queue: topic -> list of payloads. Consumers can subscribe.
_in_memory_queues: dict[str, list[dict[str, Any]]] = defaultdict(list)
_consumers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)


def get_in_memory_queues() -> dict[str, list[dict[str, Any]]]:
    return _in_memory_queues


def reset_in_memory_queues() -> None:
    _in_memory_queues.clear()
    _consumers.clear()


class InMemoryJobPublisher:
    """Publishes to in-memory list by topic. For tests and single-process dev."""

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        _in_memory_queues[topic].append(payload)
        for cb in _consumers.get(topic, []):
            try:
                cb(payload)
            except Exception as e:
                logger.exception("Consumer error for %s: %s", topic, e)

    @staticmethod
    def subscribe(topic: str, callback: Callable[[dict[str, Any]], None]) -> None:
        _consumers[topic].append(callback)

    @staticmethod
    def pop_all(topic: str) -> list[dict[str, Any]]:
        out = list(_in_memory_queues[topic])
        _in_memory_queues[topic].clear()
        return out
