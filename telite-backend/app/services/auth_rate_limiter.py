from __future__ import annotations

import math
import threading
import time
from collections import deque


_lock = threading.Lock()
_buckets: dict[str, deque[float]] = {}


def _prune(bucket: deque[float], *, now: float, window_seconds: int) -> None:
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()


def is_limited(key: str, *, limit: int, window_seconds: int) -> int | None:
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


def record_attempt(key: str, *, window_seconds: int) -> int:
    now = time.time()
    with _lock:
        bucket = _buckets.setdefault(key, deque())
        _prune(bucket, now=now, window_seconds=window_seconds)
        bucket.append(now)
        return len(bucket)


def clear_attempts(key: str) -> None:
    with _lock:
        _buckets.pop(key, None)


def clear_all_attempts() -> None:
    with _lock:
        _buckets.clear()
