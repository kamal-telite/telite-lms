"""
Benchmark Runner for Performance Validation

This module provides a configurable runner to benchmark and compare
any endpoint implementation.
"""

import json
import sys
import os
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance.query_counter import QueryCounter
from performance.benchmark import Benchmark, BenchmarkComparison
from performance.response_compare import ResponseComparator, SizeComparator


class BenchmarkConfig:
    """Configuration for a benchmark run."""

    def __init__(
        self,
        name: str,
        implementation1: Callable,
        implementation2: Optional[Callable] = None,
        description: str = "",
        runs: int = 5,
        warmup_runs: int = 1,
        ignore_fields: Optional[List[str]] = None,
        tolerance: float = 0.01,
    ):
        """
        Initialize benchmark configuration.

        Args:
            name: Benchmark name
            implementation1: First implementation (baseline)
            implementation2: Second implementation (optimized) - None if single implementation
            description: Benchmark description
            runs: Number of benchmark runs
            warmup_runs: Number of warmup runs
            ignore_fields: Fields to ignore during response comparison
            tolerance: Tolerance for floating point comparisons
        """
        self.name = name
        self.implementation1 = implementation1
        self.implementation2 = implementation2
        self.description = description
        self.runs = runs
        self.warmup_runs = warmup_runs
        self.ignore_fields = ignore_fields or []
        self.tolerance = tolerance


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.metrics1 = None
        self.metrics2 = None
        self.response1 = None
        self.response2 = None
        self.comparison = None
        self.response_comparison = None
        self.size_comparison = None
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "benchmark_name": self.config.name,
            "description": self.config.description,
            "timestamp": self.timestamp,
            "metrics1": self.metrics1,
            "metrics2": self.metrics2,
            "comparison": self.comparison,
            "response_comparison": self.response_comparison,
            "size_comparison": self.size_comparison,
        }


class BenchmarkRunner:
    """Run benchmarks and generate reports."""

    def __init__(self, query_counter: Optional[QueryCounter] = None):
        """
        Initialize benchmark runner.

        Args:
            query_counter: Optional QueryCounter instance
        """
        self.query_counter = query_counter or QueryCounter()
        self.results: List[BenchmarkResult] = []

    def attach_to_engine(self, engine):
        """Attach query counter to SQLAlchemy engine."""
        self.query_counter.attach_to_engine(engine)

    def run_benchmark(self, config: BenchmarkConfig, *args, **kwargs) -> BenchmarkResult:
        """
        Run a single benchmark.

        Args:
            config: Benchmark configuration
            *args: Arguments to pass to implementations
            **kwargs: Keyword arguments to pass to implementations

        Returns:
            BenchmarkResult instance
        """
        result = BenchmarkResult(config)

        # Benchmark implementation 1
        print(f"\nBenchmarking: {config.name}")
        print(f"Implementation 1 (baseline)...")
        benchmark1 = Benchmark(self.query_counter)
        self.query_counter.reset()
        result.metrics1 = benchmark1.benchmark_multiple_runs(
            config.implementation1,
            runs=config.runs,
            warmup_runs=config.warmup_runs,
            *args,
            **kwargs
        )
        result.response1 = benchmark1.metrics.response
        print(f"  Queries: {result.metrics1['query_count']['mean']:.1f}")
        print(f"  Time: {result.metrics1['execution_time_ms']['mean']:.2f}ms")
        print(f"  Memory: {result.metrics1['peak_memory_mb']['mean']:.2f}MB")

        # Benchmark implementation 2 (if provided)
        if config.implementation2:
            print(f"Implementation 2 (optimized)...")
            benchmark2 = Benchmark(self.query_counter)
            self.query_counter.reset()
            result.metrics2 = benchmark2.benchmark_multiple_runs(
                config.implementation2,
                runs=config.runs,
                warmup_runs=config.warmup_runs,
                *args,
                **kwargs
            )
            result.response2 = benchmark2.metrics.response
            print(f"  Queries: {result.metrics2['query_count']['mean']:.1f}")
            print(f"  Time: {result.metrics2['execution_time_ms']['mean']:.2f}ms")
            print(f"  Memory: {result.metrics2['peak_memory_mb']['mean']:.2f}MB")

            # Compare metrics
            comparison = BenchmarkComparison(result.metrics1, result.metrics2)
            result.comparison = comparison.compare()
            summary = comparison.get_summary()

            print(f"\nImprovements:")
            print(f"  Query count: {summary['query_count_improvement']:.1f}%")
            print(f"  Execution time: {summary['execution_time_improvement']:.1f}%")
            print(f"  Memory: {summary['memory_improvement']:.1f}%")

            # Compare responses
            if result.response1 is not None and result.response2 is not None:
                print(f"\nComparing responses...")
                if config.ignore_fields:
                    comparator = IgnoredFieldsComparator(config.ignore_fields, config.tolerance)
                else:
                    comparator = ResponseComparator(config.tolerance)

                identical = comparator.compare(result.response1, result.response2)
                result.response_comparison = comparator.get_summary()

                if identical:
                    print(f"  ✅ Responses are identical")
                else:
                    print(f"  ❌ Responses differ ({result.response_comparison['total_differences']} differences)")

                # Compare sizes
                result.size_comparison = SizeComparator.compare_sizes(result.response1, result.response2)
                print(f"  Size difference: {result.size_comparison['difference_bytes']} bytes ({result.size_comparison['difference_percent']:.1f}%)")

        self.results.append(result)
        return result

    def run_benchmarks(self, configs: List[BenchmarkConfig], *args, **kwargs) -> List[BenchmarkResult]:
        """
        Run multiple benchmarks.

        Args:
            configs: List of BenchmarkConfig instances
            *args: Arguments to pass to implementations
            **kwargs: Keyword arguments to pass to implementations

        Returns:
            List of BenchmarkResult instances
        """
        all_results = []
        for config in configs:
            result = self.run_benchmark(config, *args, **kwargs)
            all_results.append(result)

        return all_results

    def generate_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a benchmark report.

        Args:
            output_path: Optional path to save report as JSON

        Returns:
            Report dictionary
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_benchmarks": len(self.results),
            "benchmarks": [result.to_dict() for result in self.results],
        }

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_path}")

        return report

    def print_summary(self):
        """Print a summary of all benchmark results."""
        print(f"\n{'='*60}")
        print("Benchmark Summary")
        print(f"{'='*60}")

        for result in self.results:
            print(f"\n{result.config.name}")
            print(f"  Description: {result.config.description}")

            if result.metrics1:
                print(f"  Baseline:")
                print(f"    Queries: {result.metrics1['query_count']['mean']:.1f}")
                print(f"    Time: {result.metrics1['execution_time_ms']['mean']:.2f}ms")
                print(f"    Memory: {result.metrics1['peak_memory_mb']['mean']:.2f}MB")

            if result.metrics2:
                print(f"  Optimized:")
                print(f"    Queries: {result.metrics2['query_count']['mean']:.1f}")
                print(f"    Time: {result.metrics2['execution_time_ms']['mean']:.2f}ms")
                print(f"    Memory: {result.metrics2['peak_memory_mb']['mean']:.2f}MB")

            if result.comparison:
                summary = BenchmarkComparison(result.metrics1, result.metrics2).get_summary()
                print(f"  Improvements:")
                print(f"    Query count: {summary['query_count_improvement']:.1f}%")
                print(f"    Execution time: {summary['execution_time_improvement']:.1f}%")
                print(f"    Memory: {summary['memory_improvement']:.1f}%")

            if result.response_comparison:
                if result.response_comparison['identical']:
                    print(f"  Response: ✅ Identical")
                else:
                    print(f"  Response: ❌ {result.response_comparison['total_differences']} differences")

        print(f"\n{'='*60}")


# Convenience function for quick benchmarking
def quick_benchmark(
    implementation1: Callable,
    implementation2: Callable,
    *args,
    name: str = "benchmark",
    runs: int = 5,
    **kwargs
) -> Dict[str, Any]:
    """
    Quick benchmark two implementations.

    Args:
        implementation1: First implementation
        implementation2: Second implementation
        *args: Arguments to pass to implementations
        name: Benchmark name
        runs: Number of runs
        **kwargs: Keyword arguments to pass to implementations

    Returns:
        Benchmark results dictionary
    """
    config = BenchmarkConfig(
        name=name,
        implementation1=implementation1,
        implementation2=implementation2,
        runs=runs,
    )

    runner = BenchmarkRunner()
    result = runner.run_benchmark(config, *args, **kwargs)
    runner.print_summary()

    return result.to_dict()
