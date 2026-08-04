"""Reflection protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.reflection.models import ReflectionContext, ReflectionReport


@runtime_checkable
class ReflectionEngine(Protocol):
    """The contract for a reflection engine."""

    def reflect(self, context: ReflectionContext) -> ReflectionReport: ...
