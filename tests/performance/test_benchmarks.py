from .benchmark import BenchmarkRunner


def test_benchmark_runner_records_operations():
    runner = BenchmarkRunner(warmups=1)
    result = runner.run("arithmetic", lambda: sum(range(20)), iterations=25)
    assert result.iterations == 25
    assert result.elapsed_seconds >= 0
    assert result.average_seconds >= 0
    assert result.operations_per_second > 0
    assert len(result.samples) == 25


def test_benchmark_comparison_is_relative():
    runner = BenchmarkRunner(warmups=0)
    fast = runner.run("fast", lambda: 1 + 1, iterations=10)
    slow = runner.run("slow", lambda: sum(range(100)), iterations=10)
    comparison = runner.compare([fast, slow])
    assert comparison["fast"] == 1.0
    assert comparison["slow"] >= 0
