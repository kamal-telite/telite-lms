import json
import logging
from typing import Any
from redis import Redis

logger = logging.getLogger("telite.analytics_worker")

class AnalyticsRollupWorker:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def process_tenant_stream(self, org_id: int):
        """
        Process the Redis stream for a specific tenant and roll up metrics.
        This would typically be called by a Celery beat task.
        """
        stream_name = f"tenant:{org_id}:analytics_stream"
        
        try:
            # Read from stream (in a real scenario, use consumer groups with XREADGROUP)
            messages = self.redis.xread({stream_name: '0'}, count=100)
            if not messages:
                return

            for stream, events in messages:
                for event_id, event_data in events:
                    event_type = event_data.get(b'event_type', b'').decode('utf-8')
                    user_id = event_data.get(b'user_id', b'').decode('utf-8')
                    payload = json.loads(event_data.get(b'payload', b'{}').decode('utf-8'))
                    
                    self._process_event(org_id, event_id, event_type, user_id, payload)
                    
                    # Delete message or ACK it if using consumer groups
                    self.redis.xdel(stream_name, event_id)
                    
        except Exception as e:
            logger.error(f"Failed to process analytics stream for tenant {org_id}: {e}")

    def _process_event(self, org_id: int, event_id: bytes, event_type: str, user_id: str, payload: dict[str, Any]):
        """
        Roll up metrics based on event type.
        """
        logger.info(f"Rolling up {event_type} for org {org_id}, user {user_id}: {payload}")
        # Here we would update aggregated SQL tables (e.g., daily active users, module view counts)
        # For Phase E, we just acknowledge the event consumption to clear the stream.

def run_analytics_rollup(redis_client: Redis, active_org_ids: list[int]):
    worker = AnalyticsRollupWorker(redis_client)
    for org_id in active_org_ids:
        worker.process_tenant_stream(org_id)
