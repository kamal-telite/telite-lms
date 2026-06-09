import json
import logging
from typing import Any
from redis import Redis

logger = logging.getLogger("telite.analytics")

class AnalyticsService:
    def __init__(self, redis_client: Redis = None):
        self.redis = redis_client

    def log_event(self, event_type: str, org_id: int, user_id: str, payload: dict[str, Any]):
        """
        Push an event to the Redis stream for asynchronous processing.
        """
        if not self.redis:
            logger.warning(f"Redis not configured. Skipping event {event_type} for user {user_id}.")
            return
            
        stream_name = f"tenant:{org_id}:analytics_stream"
        
        event_data = {
            "event_type": event_type,
            "user_id": user_id,
            "payload": json.dumps(payload)
        }
        
        try:
            self.redis.xadd(stream_name, event_data)
        except Exception as e:
            logger.error(f"Failed to push event {event_type} to Redis: {e}")

# Global instance initialized elsewhere
analytics_service = AnalyticsService()
