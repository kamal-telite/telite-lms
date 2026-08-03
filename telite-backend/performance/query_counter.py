"""
SQL Query Counter for Performance Benchmarking

This module provides utilities to count and log SQL queries
executed during endpoint execution.
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from sqlalchemy import event
from sqlalchemy.engine import Engine


class QueryCounter:
    """Count and log SQL queries executed during a benchmark."""

    def __init__(self):
        self.query_count = 0
        self.query_log: List[Dict[str, Any]] = []
        self.query_stats = defaultdict(int)
        self._listener_attached = False

    def attach_to_engine(self, engine: Engine):
        """Attach query counting listener to SQLAlchemy engine."""
        if self._listener_attached:
            return

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            self.query_count += 1
            self.query_log.append({
                "query": statement,
                "parameters": parameters,
                "timestamp": datetime.utcnow().isoformat(),
                "executemany": executemany,
            })
            # Track query patterns (normalize parameters)
            normalized = self._normalize_query(statement)
            self.query_stats[normalized] += 1

        self._listener_attached = True

    def reset(self):
        """Reset query counters."""
        self.query_count = 0
        self.query_log = []
        self.query_stats = defaultdict(int)

    def get_count(self) -> int:
        """Get total query count."""
        return self.query_count

    def get_log(self) -> List[Dict[str, Any]]:
        """Get query log."""
        return self.query_log

    def get_stats(self) -> Dict[str, int]:
        """Get query statistics (pattern frequency)."""
        return dict(self.query_stats)

    def _normalize_query(self, query: str) -> str:
        """Normalize query by replacing parameters with placeholders."""
        # Simple normalization - replace string literals and numbers
        import re
        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of query execution."""
        return {
            "total_queries": self.query_count,
            "unique_query_patterns": len(self.query_stats),
            "query_pattern_frequency": dict(sorted(
                self.query_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )),
            "first_query_time": self.query_log[0]["timestamp"] if self.query_log else None,
            "last_query_time": self.query_log[-1]["timestamp"] if self.query_log else None,
        }


class QueryCounterContext:
    """Context manager for automatic query counting."""

    def __init__(self, counter: QueryCounter):
        self.counter = counter
        self.original_count = 0

    def __enter__(self):
        self.original_count = self.counter.get_count()
        return self.counter

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_queries_in_context(self) -> int:
        """Get number of queries executed within this context."""
        return self.counter.get_count() - self.original_count
