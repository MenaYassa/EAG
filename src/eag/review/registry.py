"""Analyzer registry for EAG."""

from eag.review.errors import ReviewError
from eag.review.models import ReviewAnalyzer


class AnalyzerRegistry:
    """Discovers and manages available review analyzers."""

    def __init__(self) -> None:
        self._analyzers: dict[str, ReviewAnalyzer] = {}

    def register(self, name: str, analyzer: ReviewAnalyzer) -> None:
        if name in self._analyzers:
            raise ReviewError(f"Analyzer '{name}' is already registered.")
        self._analyzers[name] = analyzer

    def list(self) -> tuple[ReviewAnalyzer, ...]:
        return tuple(self._analyzers.values())