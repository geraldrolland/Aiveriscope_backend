"""Celery application instance wired to the Redis broker/result backend."""
from celery import Celery

from .config import settings

celery_app = Celery(
    "fakenews",
    broker=settings.redis_url,
    backend=settings.redis_result_url,
    include=["app.tasks"],
)

_redis_options = {
    "health_check_interval": settings.redis_health_check_interval,
    "socket_timeout": settings.redis_socket_timeout,
    "socket_connect_timeout": settings.redis_socket_connect_timeout,
    "socket_keepalive": settings.redis_socket_keepalive,
    "retry_on_timeout": True,
}

celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_transport_options=_redis_options,
    redis_socket_timeout=settings.redis_socket_timeout,
    redis_retry_on_timeout=True,
    redis_socket_keepalive=settings.redis_socket_keepalive,
    redis_backend_health_check_interval=settings.redis_health_check_interval,
)
