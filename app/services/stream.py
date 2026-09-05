"""Subscribe to analysis task events and yield them one by one."""
import json
from collections.abc import AsyncGenerator

import redis.asyncio as aredis

from ..config import settings


async def event_stream(task_id: str) -> AsyncGenerator[dict | None, None]:
    """Yield parsed events from the task's pub/sub channel.

    Yields None as a heartbeat whenever the channel is idle, so the caller
    can re-check the task's state (e.g. after a reconnection).
    """
    client = aredis.from_url(
        settings.redis_url,
        decode_responses=True,
        health_check_interval=settings.redis_health_check_interval,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_keepalive=settings.redis_socket_keepalive,
    )
    pubsub = client.pubsub()
    name = f"analyze:{task_id}"
    await pubsub.subscribe(name)
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=settings.ws_idle_timeout
            )
            if message is None:
                yield None
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(name)
        await pubsub.aclose()
        await client.aclose()
