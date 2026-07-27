"""Execution provider protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    ProviderHealth,
)
from eag.chief.intelligence.models import ModelProfile


@runtime_checkable
class AIProvider(Protocol):
    """The contract for an AI execution provider."""

    @property
    def provider_id(self) -> str: ...

    def execute(self, context: ExecutionContext) -> ExecutionResult: ...

    def health(self) -> ProviderHealth: ...

    def models(self) -> tuple[ModelProfile, ...]: ...

    def supports(self, model_id: str) -> bool: ...