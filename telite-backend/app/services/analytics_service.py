import json
import logging
import os
from typing import Any
from redis import Redis

logger = logging.getLogger("telite.analytics")

class AnalyticsService:
    def __init__(self, redis_client: Redis = None):
        self.redis = redis_client

    def _get_redis(self) -> Redis | None:
        if self.redis:
            return self.redis

        if os.getenv("REDIS_ENABLED", "true").lower() not in ("1", "true", "yes"):
            return None

        host = os.getenv("REDIS_HOST")
        if not host:
            return None

        try:
            self.redis = Redis(
                host=host,
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD") or None,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self.redis.ping()
        except Exception as exc:
            logger.warning("Redis analytics connection unavailable: %s", exc)
            self.redis = None

        return self.redis

    def log_event(self, event_type: str, org_id: int, user_id: str, payload: dict[str, Any]):
        """
        Push an event to the Redis stream for asynchronous processing.
        """
        redis_client = self._get_redis()
        if not redis_client:
            logger.warning(f"Redis not configured. Skipping event {event_type} for user {user_id}.")
            return
            
        stream_name = f"tenant:{org_id}:analytics_stream"
        
        event_data = {
            "event_type": event_type,
            "user_id": user_id,
            "payload": json.dumps(payload)
        }
        
        try:
            redis_client.xadd(stream_name, event_data)
        except Exception as e:
            logger.error(f"Failed to push event {event_type} to Redis: {e}")

# Global instance initialized elsewhere
analytics_service = AnalyticsService()
