"""
Distributed rate limiter using Redis.

This module provides Redis-backed rate limiting to replace the in-memory
implementation, enabling distributed rate limiting across multiple workers
and containers.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import deque
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


logger = logging.getLogger("telite.rate_limiter")


# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")

# Fallback in-memory storage (for development or Redis unavailable)
_lock = threading.Lock()
_buckets: dict[str, deque[float]] = {}

# Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def _get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client with connection pooling."""
    global _redis_pool, _redis_client
    
    if not REDIS_ENABLED:
        return None
    
    if not REDIS_AVAILABLE:
        logger.warning(
            "Redis rate limiting requested but redis package not installed. "
            "Falling back to in-memory rate limiting. "
            "Install redis with: pip install redis"
        )
        return None
    
    if _redis_client is None:
        try:
            _redis_pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                db=REDIS_DB,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis rate limiter connected to {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(
                f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}. "
                "Falling back to in-memory rate limiting."
            )
            _redis_client = None
            _redis_pool = None
    
    return _redis_client


def _redis_is_limited(key: str, *, limit: int, window_seconds: int) -> Optional[int]:
    """Check if rate limit is exceeded using Redis sorted sets."""
    client = _get_redis_client()
    if client is None:
        return None
    
    try:
        now = time.time()
        cutoff = now - window_seconds
        
        # Remove old entries
        client.zremrangebyscore(key, 0, cutoff)
        
        # Count current entries
        count = client.zcard(key)
        
        if count < limit:
            return None
        
        # Get oldest entry to calculate retry_after
        oldest = client.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_time = oldest[0][1]
            retry_after = max(1, int(math.ceil(window_seconds - (now - oldest_time))))
            return retry_after
        
        return None
        
    except Exception as e:
        logger.error(f"Redis rate limit check failed: {e}. Falling back to in-memory.")
        return None


def _redis_record_attempt(key: str, *, window_seconds: int) -> int:
    """Record a rate limit attempt using Redis sorted sets."""
    client = _get_redis_client()
    if client is None:
        return 0
    
    try:
        now = time.time()
        cutoff = now - window_seconds
        
        # Remove old entries
        client.zremrangebyscore(key, 0, cutoff)
        
        # Add new entry
        client.zadd(key, {str(now): now})
        
        # Set expiration to window_seconds + buffer
        client.expire(key, window_seconds + 60)
        
        # Return current count
        return client.zcard(key)
        
    except Exception as e:
        logger.error(f"Redis record attempt failed: {e}. Falling back to in-memory.")
        return 0


def _redis_clear_attempts(key: str) -> None:
    """Clear rate limit attempts for a key using Redis."""
    client = _get_redis_client()
    if client is None:
        return
    
    try:
        client.delete(key)
    except Exception as e:
        logger.error(f"Redis clear attempts failed: {e}")


# Fallback in-memory implementation


def _prune(bucket: deque[float], *, now: float, window_seconds: int) -> None:
    """Remove expired entries from in-memory bucket."""
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()


def _memory_is_limited(key: str, *, limit: int, window_seconds: int) -> Optional[int]:
    """Check if rate limit is exceeded using in-memory storage."""
    now = time.time()
    with _lock:
        bucket = _buckets.get(key)
        if not bucket:
            return None
        _prune(bucket, now=now, window_seconds=window_seconds)
        if not bucket:
            _buckets.pop(key, None)
            return None
        if len(bucket) < limit:
            return None
        retry_after = max(1, int(math.ceil(window_seconds - (now - bucket[0]))))
        return retry_after


def _memory_record_attempt(key: str, *, window_seconds: int) -> int:
    """Record a rate limit attempt using in-memory storage."""
    now = time.time()
    with _lock:
        bucket = _buckets.setdefault(key, deque())
        _prune(bucket, now=now, window_seconds=window_seconds)
        bucket.append(now)
        return len(bucket)


def _memory_clear_attempts(key: str) -> None:
    """Clear rate limit attempts for a key using in-memory storage."""
    with _lock:
        _buckets.pop(key, None)


# Public API


def is_limited(key: str, *, limit: int, window_seconds: int) -> Optional[int]:
    """
    Check if a rate limit has been exceeded.
    
    Args:
        key: Unique identifier for the rate limit bucket
        limit: Maximum number of attempts allowed
        window_seconds: Time window in seconds
        
    Returns:
        Number of seconds to wait before retrying, or None if not limited
    """
    # Try Redis first
    result = _redis_is_limited(key, limit=limit, window_seconds=window_seconds)
    if result is not None:
        return result
    
    # Fallback to in-memory
    return _memory_is_limited(key, limit=limit, window_seconds=window_seconds)


def record_attempt(key: str, *, window_seconds: int) -> int:
    """
    Record a rate limit attempt.
    
    Args:
        key: Unique identifier for the rate limit bucket
        window_seconds: Time window in seconds
        
    Returns:
        Current number of attempts in the window
    """
    # Try Redis first
    count = _redis_record_attempt(key, window_seconds=window_seconds)
    if count > 0:
        return count
    
    # Fallback to in-memory
    return _memory_record_attempt(key, window_seconds=window_seconds)


def clear_attempts(key: str) -> None:
    """
    Clear all rate limit attempts for a key.
    
    Args:
        key: Unique identifier for the rate limit bucket
    """
    # Clear from both Redis and memory
    _redis_clear_attempts(key)
    _memory_clear_attempts(key)


def clear_all_attempts() -> None:
    """Clear all rate limit attempts (in-memory only)."""
    with _lock:
        _buckets.clear()
    
    # Note: We don't clear all Redis keys as that would affect other services
    logger.warning("clear_all_attempts() only clears in-memory buckets, not Redis")


def close_redis_connection() -> None:
    """Close Redis connection pool."""
    global _redis_client, _redis_pool
    
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
    
    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")
        finally:
            _redis_pool = None
