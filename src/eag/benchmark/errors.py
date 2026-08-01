"""Benchmark domain errors for EAG."""


class BenchmarkError(Exception):
    """Base error for all benchmark failures."""


class RegistryError(BenchmarkError):
    """Raised when registry operations fail."""


class EvaluationError(BenchmarkError):
    """Raised when evaluation fails."""


class RunnerError(BenchmarkError):
    """Raised when benchmark execution fails."""


class FixtureError(BenchmarkError):
    """Raised when fixture preparation fails."""
