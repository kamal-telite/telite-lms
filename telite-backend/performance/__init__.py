"""
Performance Benchmarking Framework

This package provides a reusable framework for benchmarking
and validating performance optimizations in the backend.

Modules:
    query_counter: SQL query counting and logging
    response_compare: JSON response comparison
    benchmark: Performance benchmarking utilities
    benchmark_runner: Configurable benchmark runner

Example usage:
    from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig
    from performance.query_counter import QueryCounter
    from app.db.engine import engine

    # Initialize
    query_counter = QueryCounter()
    query_counter.attach_to_engine(engine)
    runner = BenchmarkRunner(query_counter)

    # Define implementations
    def original_implementation():
        # Original code
        pass

    def optimized_implementation():
        # Optimized code
        pass

    # Create config
    config = BenchmarkConfig(
        name="quiz_statistics",
        implementation1=original_implementation,
        implementation2=optimized_implementation,
        description="Quiz Statistics endpoint optimization",
        runs=5,
    )

    # Run benchmark
    result = runner.run_benchmark(config)
    runner.print_summary()
    runner.generate_report("benchmark_results.json")
"""

from performance.query_counter import QueryCounter, QueryCounterContext
from performance.response_compare import ResponseComparator, IgnoredFieldsComparator, SizeComparator
from performance.benchmark import Benchmark, BenchmarkMetrics, BenchmarkComparison
from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig, BenchmarkResult, quick_benchmark

__all__ = [
    "QueryCounter",
    "QueryCounterContext",
    "ResponseComparator",
    "IgnoredFieldsComparator",
    "SizeComparator",
    "Benchmark",
    "BenchmarkMetrics",
    "BenchmarkComparison",
    "BenchmarkRunner",
    "BenchmarkConfig",
    "BenchmarkResult",
    "quick_benchmark",
]
