"""Lightweight performance harness for deterministic service benchmarks."""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    iterations: int
    elapsed_seconds: float
    average_seconds: float
    operations_per_second: float
    samples: tuple[float, ...]

    @property
    def milliseconds_per_operation(self) -> float:
        return self.average_seconds * 1000


class BenchmarkRunner:
    """Runs repeatable microbenchmarks without external benchmark packages."""

    def __init__(self, warmups: int = 2):
        self.warmups = max(0, warmups)

    def run(self, name: str, operation: Callable[[], T], iterations: int = 100) -> BenchmarkResult:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        for _ in range(self.warmups):
            operation()
        samples = []
        started = time.perf_counter()
        for _ in range(iterations):
            sample_start = time.perf_counter()
            operation()
            samples.append(time.perf_counter() - sample_start)
        elapsed = time.perf_counter() - started
        average = statistics.fmean(samples)
        return BenchmarkResult(name, iterations, elapsed, average, iterations / elapsed if elapsed else float("inf"), tuple(samples))

    @staticmethod
    def compare(results: list[BenchmarkResult]) -> dict[str, float]:
        if not results:
            return {}
        baseline = results[0].average_seconds
        return {result.name: result.average_seconds / baseline if baseline else 0.0 for result in results}
