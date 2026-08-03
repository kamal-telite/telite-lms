# Performance Benchmarking Framework

A reusable framework for benchmarking and validating performance optimizations in the Telite LMS backend.

## Overview

This framework provides tools to:
- Count SQL queries executed during endpoint execution
- Measure API execution time, CPU time, and memory usage
- Compare JSON responses between implementations to ensure behavioral equivalence
- Generate performance reports with before/after comparisons
- Validate optimizations without writing custom benchmark scripts for each endpoint

## Installation

The framework is included in the `performance/` directory. No additional installation required.

## Quick Start

### Basic Benchmarking

```python
from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig
from performance.query_counter import QueryCounter
from app.db.engine import engine

# Initialize
query_counter = QueryCounter()
query_counter.attach_to_engine(engine)
runner = BenchmarkRunner(query_counter)

# Define implementations
def original_implementation():
    # Your original code
    return {"result": "data"}

def optimized_implementation():
    # Your optimized code
    return {"result": "data"}

# Create config
config = BenchmarkConfig(
    name="my_endpoint",
    implementation1=original_implementation,
    implementation2=optimized_implementation,
    description="My endpoint optimization",
    runs=5,
)

# Run benchmark
result = runner.run_benchmark(config)
runner.print_summary()
runner.generate_report("benchmark_results.json")
```

### Quick Benchmarking (Convenience Function)

```python
from performance.benchmark_runner import quick_benchmark

result = quick_benchmark(
    original_implementation,
    optimized_implementation,
    name="my_endpoint",
    runs=5
)
```

## Components

### 1. Query Counter (`query_counter.py`)

Counts and logs SQL queries executed during benchmark execution.

**Features:**
- Total query count
- Query log with timestamps
- Query pattern frequency analysis
- Normalized query tracking

**Usage:**
```python
from performance.query_counter import QueryCounter

counter = QueryCounter()
counter.attach_to_engine(engine)

# Execute code
counter.reset()  # Reset before benchmark
# ... run code ...
count = counter.get_count()
log = counter.get_log()
stats = counter.get_stats()
summary = counter.get_summary()
```

### 2. Response Comparator (`response_compare.py`)

Compares JSON responses to ensure behavioral equivalence.

**Features:**
- Recursive comparison of nested structures
- Floating point tolerance
- Field ignoring support
- Size comparison

**Usage:**
```python
from performance.response_compare import ResponseComparator, IgnoredFieldsComparator

# Basic comparison
comparator = ResponseComparator(tolerance=0.01)
identical = comparator.compare(response1, response2)
differences = comparator.get_differences()
summary = comparator.get_summary()

# Ignore specific fields (e.g., timestamps)
comparator = IgnoredFieldsComparator(
    ignored_fields=["rows[*].created_at", "rows[*].updated_at"],
    tolerance=0.01
)
identical = comparator.compare(response1, response2)
```

### 3. Benchmark (`benchmark.py`)

Measures performance metrics during code execution.

**Features:**
- Execution time measurement
- CPU time measurement
- Memory usage tracking
- Response size measurement
- Multiple run aggregation with statistics

**Usage:**
```python
from performance.benchmark import Benchmark

benchmark = Benchmark(query_counter)

# Single run
metrics = benchmark.benchmark_function(my_function, arg1, arg2)

# Multiple runs with aggregation
metrics = benchmark.benchmark_multiple_runs(
    my_function,
    runs=5,
    warmup_runs=1,
    arg1,
    arg2
)
```

### 4. Benchmark Runner (`benchmark_runner.py`)

Configurable runner for executing benchmarks and generating reports.

**Features:**
- Multiple benchmark execution
- Before/after comparison
- Automatic report generation
- Summary printing

**Usage:**
```python
from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig

runner = BenchmarkRunner(query_counter)

config = BenchmarkConfig(
    name="endpoint_name",
    implementation1=original_func,
    implementation2=optimized_func,
    description="Description",
    runs=5,
    warmup_runs=1,
    ignore_fields=None,  # Optional: fields to ignore during comparison
    tolerance=0.01,
)

result = runner.run_benchmark(config, arg1, arg2)
runner.print_summary()
runner.generate_report("output.json")
```

## Benchmarking an Endpoint

### Step 1: Define Implementations

Create two functions that implement the endpoint logic:

```python
def quiz_statistics_original(db, category_slug, current_user):
    """Original N+1 implementation."""
    # Original code here
    return {"rows": [...]}

def quiz_statistics_optimized(db, category_slug, current_user):
    """Optimized batch-query implementation."""
    # Optimized code here
    return {"rows": [...]}
```

### Step 2: Create Benchmark Script

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig
from performance.query_counter import QueryCounter
from app.db.engine import engine, db_session
from app.api.auth import TokenData

# Initialize
query_counter = QueryCounter()
query_counter.attach_to_engine(engine)
runner = BenchmarkRunner(query_counter)

# Setup test data
category_slug = "ats"
org_id = 1
user_id = "test_user"

# Create mock token
current_user = TokenData(
    id=user_id,
    email="test@example.com",
    role="category_admin",
    org_id=org_id,
    category_scope=category_slug,
    is_platform_admin=False,
)

# Define benchmark config
config = BenchmarkConfig(
    name="quiz_statistics",
    implementation1=lambda: quiz_statistics_original(db, category_slug, current_user),
    implementation2=lambda: quiz_statistics_optimized(db, category_slug, current_user),
    description="Quiz Statistics endpoint - N+1 to batch query optimization",
    runs=5,
    warmup_runs=1,
)

# Run benchmark
with db_session() as db:
    result = runner.run_benchmark(config)
    runner.print_summary()
    runner.generate_report("quiz_statistics_benchmark.json")
```

### Step 3: Run the Benchmark

```bash
python benchmark_quiz_statistics.py
```

### Step 4: Review Results

The output will show:
- Query count before and after
- Execution time before and after
- Memory usage before and after
- Response comparison (identical or differences)
- Improvement percentages

## Benchmark Configuration Options

### BenchmarkConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | Required | Benchmark name |
| `implementation1` | Callable | Required | Baseline implementation |
| `implementation2` | Callable | Optional | Optimized implementation |
| `description` | str | "" | Benchmark description |
| `runs` | int | 5 | Number of benchmark runs |
| `warmup_runs` | int | 1 | Number of warmup runs |
| `ignore_fields` | List[str] | None | Fields to ignore during comparison |
| `tolerance` | float | 0.01 | Floating point tolerance |

### Ignoring Fields

Use `ignore_fields` to exclude fields that may legitimately differ (e.g., timestamps):

```python
config = BenchmarkConfig(
    name="my_endpoint",
    implementation1=original_func,
    implementation2=optimized_func,
    ignore_fields=[
        "rows[*].created_at",
        "rows[*].updated_at",
        "timestamp",
    ],
)
```

## Interpreting Results

### Benchmark Metrics

**Query Count:**
- Number of SQL queries executed
- Lower is better
- Target: Significant reduction (e.g., 90%+)

**Execution Time:**
- Wall-clock time in milliseconds
- Lower is better
- Target: Significant reduction (e.g., 50%+)

**CPU Time:**
- CPU time in milliseconds
- Lower is better
- Indicates computational efficiency

**Memory Usage:**
- Peak memory in MB
- Lower is better
- Monitor for memory leaks

**Response Comparison:**
- `identical: true` - Responses are behaviorally equivalent
- `identical: false` - Responses differ (review differences)

### Example Output

```
Benchmarking: quiz_statistics
Implementation 1 (baseline)...
  Queries: 1002.0
  Time: 15234.50ms
  Memory: 45.23MB
Implementation 2 (optimized)...
  Queries: 3.0
  Time: 2450.75ms
  Memory: 48.12MB

Improvements:
  Query count: 99.7%
  Execution time: 83.9%
  Memory: -6.4%

Comparing responses...
  ✅ Responses are identical
  Size difference: 0 bytes (0.0%)
```

## Benchmarking Different Endpoints

### Quiz Statistics

```python
config = BenchmarkConfig(
    name="quiz_statistics",
    implementation1=quiz_statistics_original,
    implementation2=quiz_statistics_optimized,
    description="Quiz Statistics - N+1 to batch query",
)
```

### Certificates

```python
config = BenchmarkConfig(
    name="certificates",
    implementation1=certificates_original,
    implementation2=certificates_optimized,
    description="Certificates - N+1 course fetch to JOIN",
    ignore_fields=["rows[*].issued_at"],  # Timestamps may differ
)
```

### Announcements

```python
config = BenchmarkConfig(
    name="announcements",
    implementation1=announcements_original,
    implementation2=announcements_optimized,
    description="Announcements - N+1 notification creation to bulk insert",
)
```

### Audit Timeline

```python
config = BenchmarkConfig(
    name="audit_timeline",
    implementation1=audit_timeline_original,
    implementation2=audit_timeline_optimized,
    description="Audit Timeline - Python pagination to database pagination",
)
```

## Report Format

Benchmark reports are saved as JSON with the following structure:

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "total_benchmarks": 1,
  "benchmarks": [
    {
      "benchmark_name": "quiz_statistics",
      "description": "Quiz Statistics optimization",
      "timestamp": "2024-01-15T10:30:00",
      "metrics1": {
        "query_count": {"mean": 1002, "min": 980, "max": 1020},
        "execution_time_ms": {"mean": 15234, "min": 15000, "max": 15500},
        "peak_memory_mb": {"mean": 45.2, "min": 44.0, "max": 46.0}
      },
      "metrics2": {
        "query_count": {"mean": 3, "min": 3, "max": 3},
        "execution_time_ms": {"mean": 2450, "min": 2400, "max": 2500},
        "peak_memory_mb": {"mean": 48.1, "min": 47.0, "max": 49.0}
      },
      "comparison": {
        "query_count_reduction_percent": 99.7,
        "execution_time_ms_reduction_percent": 83.9
      },
      "response_comparison": {
        "identical": true,
        "total_differences": 0
      }
    }
  ]
}
```

## Best Practices

1. **Use Warmup Runs**: Always include warmup runs to allow database connection pooling and query plan caching.

2. **Multiple Runs**: Use multiple runs (5-10) to account for variance and get statistically significant results.

3. **Response Comparison**: Always compare responses to ensure behavioral equivalence. Use `ignore_fields` for legitimate differences (timestamps, IDs).

4. **Monitor Memory**: Check memory usage to ensure optimizations don't introduce memory leaks.

5. **Test with Real Data**: Benchmark with realistic dataset sizes to predict production performance.

6. **Isolate Environment**: Run benchmarks in a staging environment with similar hardware to production.

7. **Save Reports**: Save benchmark reports for historical comparison and regression detection.

## Troubleshooting

### Query Counter Not Working

Ensure the query counter is attached to the engine before any queries are executed:

```python
query_counter = QueryCounter()
query_counter.attach_to_engine(engine)  # Must be called first
```

### Responses Differ Unexpectedly

1. Check for floating point precision issues - increase tolerance
2. Check for timestamp differences - add to `ignore_fields`
3. Check for ID differences - these may be legitimate if using auto-increment
4. Review the `differences` list in the report for specific issues

### Memory Usage High

1. Check if the optimization loads large datasets into memory
2. Consider using database-level pagination
3. Profile memory usage with tools like `memory_profiler`

### No Performance Improvement

1. Verify the optimization is actually being executed
2. Check if database indexes are missing
3. Review query execution plans with `EXPLAIN ANALYZE`
4. Ensure benchmark dataset is large enough to show improvement

## Advanced Usage

### Custom Metrics

Extend the `BenchmarkMetrics` class to track custom metrics:

```python
class CustomBenchmarkMetrics(BenchmarkMetrics):
    def __init__(self):
        super().__init__()
        self.custom_metric = 0
```

### Multiple Endpoints

Benchmark multiple endpoints in a single run:

```python
configs = [
    BenchmarkConfig(name="endpoint1", ...),
    BenchmarkConfig(name="endpoint2", ...),
    BenchmarkConfig(name="endpoint3", ...),
]

results = runner.run_benchmarks(configs)
runner.print_summary()
runner.generate_report("multi_endpoint_benchmark.json")
```

### Conditional Benchmarking

Run benchmarks only if certain conditions are met:

```python
if os.getenv("RUN_BENCHMARKS") == "true":
    runner.run_benchmark(config)
```

## Contributing

When adding new benchmark capabilities:

1. Update this README
2. Add examples to the documentation
3. Ensure backward compatibility
4. Add unit tests for new features

## License

This framework is part of the Telite LMS backend project.
