"""Engineering-context assembly boundary for governed decision requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from eag.chief.intelligence.gateway.models import EngineeringContext


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextAssemblyRequest:
    """Inputs available to a context assembler before any model interaction."""

    goal: str
    repository_path: Path | None
    available_capabilities: tuple[str, ...]
    known_constraints: tuple[str, ...] = ()


@runtime_checkable
class EngineeringContextAssembler(Protocol):
    """Builds bounded factual context without invoking a provider or capability."""

    def assemble(self, request: ContextAssemblyRequest) -> EngineeringContext: ...


class DefaultEngineeringContextAssembler:
    """Creates a minimal, non-mutating context from explicit deterministic inputs."""

    def assemble(self, request: ContextAssemblyRequest) -> EngineeringContext:
        repository_identity = ""
        repository_summary = "No repository context was supplied."
        provenance: dict[str, str] = {
            "goal": "caller",
            "available_capabilities": "caller",
            "known_constraints": "caller",
        }

        if request.repository_path is not None:
            root = request.repository_path.resolve()
            repository_identity = str(root)
            repository_summary = f"Repository root supplied by caller: {root.name}"
            provenance["repository_identity"] = "caller.repository_path"

        return EngineeringContext(
            repository_identity=repository_identity,
            repository_summary=repository_summary,
            known_constraints=request.known_constraints,
            available_capabilities=request.available_capabilities,
            provenance=provenance,
            truncation_metadata={"source_content_included": False},
        )
