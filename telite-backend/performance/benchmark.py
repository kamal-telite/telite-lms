"""
Performance Benchmarking Framework

This module provides utilities to benchmark endpoint performance
including query count, execution time, memory usage, and CPU time.
"""

import time
import tracemalloc
import psutil
import os
from typing import Dict, Any, Callable, Optional, List
from contextlib import contextmanager
from datetime import datetime

from performance.query_counter import QueryCounter


class BenchmarkMetrics:
    """Container for benchmark metrics."""

    def __init__(self):
        self.query_count = 0
        self.execution_time_ms = 0.0
        self.cpu_time_ms = 0.0
        self.peak_memory_mb = 0.0
        self.memory_delta_mb = 0.0
        self.response_size_bytes = 0
        self.response = None
        self.query_stats = {}
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "query_count": self.query_count,
            "execution_time_ms": self.execution_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "memory_delta_mb": self.memory_delta_mb,
            "response_size_bytes": self.response_size_bytes,
            "query_stats": self.query_stats,
            "timestamp": self.timestamp,
        }


class Benchmark:
    """Benchmark a function or endpoint."""

    def __init__(self, query_counter: Optional[QueryCounter] = None):
        """
        Initialize benchmark.

        Args:
            query_counter: Optional QueryCounter instance
        """
        self.query_counter = query_counter or QueryCounter()
        self.metrics = BenchmarkMetrics()

    @contextmanager
    def measure(self, track_response: bool = True):
        """
        Context manager to measure code execution.

        Args:
            track_response: Whether to track response size

        Yields:
            None
        """
        # Start measurements
        tracemalloc.start()
        start_time = time.time()
        start_cpu = time.process_time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Reset query counter
        initial_query_count = self.query_counter.get_count()

        try:
            yield
        finally:
            # End measurements
            end_time = time.time()
            end_cpu = time.process_time()
            end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Calculate metrics
            self.metrics.query_count = self.query_counter.get_count() - initial_query_count
            self.metrics.execution_time_ms = (end_time - start_time) * 1000
            self.metrics.cpu_time_ms = (end_cpu - start_cpu) * 1000
            self.metrics.peak_memory_mb = peak / 1024 / 1024
            self.metrics.memory_delta_mb = end_memory - start_memory
            self.metrics.query_stats = self.query_counter.get_stats()
            self.metrics.timestamp = datetime.utcnow().isoformat()

    def benchmark_function(
        self,
        func: Callable,
        *args,
        track_response: bool = True,
        **kwargs
    ) -> BenchmarkMetrics:
        """
        Benchmark a function.

        Args:
            func: Function to benchmark
            *args: Function arguments
            track_response: Whether to track response size
            **kwargs: Function keyword arguments

        Returns:
            BenchmarkMetrics instance
        """
        with self.measure(track_response=track_response):
            result = func(*args, **kwargs)

        # Track response size if requested
        if track_response and result is not None:
            import json
            json_str = json.dumps(result, default=str)
            self.metrics.response_size_bytes = len(json_str.encode('utf-8'))
            self.metrics.response = result

        return self.metrics

    def benchmark_multiple_runs(
        self,
        func: Callable,
        runs: int = 5,
        warmup_runs: int = 1,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Benchmark a function multiple times and aggregate results.

        Args:
            func: Function to benchmark
            runs: Number of benchmark runs
            warmup_runs: Number of warmup runs (not included in results)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Aggregated benchmark results
        """
        # Warmup runs
        for _ in range(warmup_runs):
            func(*args, **kwargs)

        # Benchmark runs
        metrics_list = []
        for _ in range(runs):
            metrics = self.benchmark_function(func, *args, **kwargs)
            metrics_list.append(metrics.to_dict())

        # Aggregate results
        aggregated = self._aggregate_metrics(metrics_list)
        aggregated["runs"] = runs
        aggregated["warmup_runs"] = warmup_runs

        return aggregated

    def _aggregate_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics from multiple runs."""
        if not metrics_list:
            return {}

        keys = metrics_list[0].keys()
        aggregated = {}

        for key in keys:
            values = [m[key] for m in metrics_list if m[key] is not None]

            if not values:
                aggregated[key] = None
            elif isinstance(values[0], (int, float)):
                aggregated[key] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "std": self._std_dev(values),
                }
            else:
                aggregated[key] = values[0]  # Non-numeric values, take first

        return aggregated

    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


class BenchmarkComparison:
    """Compare benchmark results between two implementations."""

    def __init__(self, metrics1: Dict[str, Any], metrics2: Dict[str, Any]):
        """
        Initialize comparison.

        Args:
            metrics1: Metrics from first implementation
            metrics2: Metrics from second implementation
        """
        self.metrics1 = metrics1
        self.metrics2 = metrics2

    def compare(self) -> Dict[str, Any]:
        """
        Compare metrics and calculate improvements.

        Returns:
            Comparison results
        """
        comparison = {
            "implementation1": self.metrics1,
            "implementation2": self.metrics2,
            "improvements": {},
        }

        # Compare numeric metrics
        numeric_fields = [
            "query_count",
            "execution_time_ms",
            "cpu_time_ms",
            "peak_memory_mb",
            "memory_delta_mb",
            "response_size_bytes",
        ]

        for field in numeric_fields:
            val1 = self._get_numeric_value(self.metrics1, field)
            val2 = self._get_numeric_value(self.metrics2, field)

            if val1 is not None and val2 is not None:
                if val1 > 0:
                    improvement = ((val1 - val2) / val1) * 100
                    comparison["improvements"][f"{field}_reduction_percent"] = improvement
                else:
                    comparison["improvements"][f"{field}_reduction_percent"] = 0.0

                comparison["improvements"][f"{field}_difference"] = val2 - val1

        return comparison

    def _get_numeric_value(self, metrics: Dict[str, Any], field: str) -> Optional[float]:
        """Extract numeric value from metrics (handles aggregated results)."""
        value = metrics.get(field)

        if value is None:
            return None

        if isinstance(value, dict):
            # Aggregated metrics (mean, min, max, std)
            return value.get("mean", 0.0)

        return float(value)

    def get_summary(self) -> Dict[str, Any]:
        """Get human-readable summary of comparison."""
        comparison = self.compare()
        improvements = comparison["improvements"]

        summary = {
            "query_count_improvement": improvements.get("query_count_reduction_percent", 0),
            "execution_time_improvement": improvements.get("execution_time_ms_reduction_percent", 0),
            "memory_improvement": improvements.get("peak_memory_mb_reduction_percent", 0),
            "significant_improvements": [],
            "regressions": [],
        }

        # Identify significant improvements (>10%)
        if summary["query_count_improvement"] > 10:
            summary["significant_improvements"].append(f"Query count reduced by {summary['query_count_improvement']:.1f}%")
        if summary["execution_time_improvement"] > 10:
            summary["significant_improvements"].append(f"Execution time reduced by {summary['execution_time_improvement']:.1f}%")

        # Identify regressions (<0% improvement, i.e., worse performance)
        if summary["query_count_improvement"] < 0:
            summary["regressions"].append(f"Query count increased by {abs(summary['query_count_improvement']):.1f}%")
        if summary["execution_time_improvement"] < 0:
            summary["regressions"].append(f"Execution time increased by {abs(summary['execution_time_improvement']):.1f}%")

        return summary
