"""URL-keyed result cache backed by Redis."""
import json

import redis

from ..config import settings

_client: redis.Redis | None = None


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


def normalize_url(url: str) -> str:
    """Normalize a pasted URL so equivalent variants share one cache key."""
    return url.strip().rstrip("/")


def _key(url: str) -> str:
    return f"url_cache:{normalize_url(url)}"


def cache_get(url: str) -> dict | None:
    """Return the cached analysis payload for a URL, or None on miss."""
    if not settings.cache_enabled:
        return None
    try:
        raw = get_client().get(_key(url))
    except redis.RedisError:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def cache_set(url: str, payload: dict) -> None:
    """Store an analysis payload for a URL with the configured TTL."""
    if not settings.cache_enabled:
        return
    try:
        get_client().set(_key(url), json.dumps(payload), ex=settings.cache_ttl_seconds)
    except redis.RedisError:
        pass
