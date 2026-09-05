"""Publish progress/result events for analysis tasks via Redis pub/sub."""
import json

import redis

from ..config import settings

_client: redis.Redis | None = None


def channel(task_id: str) -> str:
    return f"analyze:{task_id}"


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=settings.redis_health_check_interval,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_keepalive=settings.redis_socket_keepalive,
        )
    return _client


def publish(task_id: str, event: dict) -> None:
    get_client().publish(channel(task_id), json.dumps(event))
