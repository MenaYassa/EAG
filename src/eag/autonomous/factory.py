"""Canonical composition for the deterministic autonomous engineering path."""

from dataclasses import dataclass
from pathlib import Path

from eag.adaptive import AdaptivePlanner
from eag.autonomous.runtime import AutonomousLoopRuntime
from eag.capability import (
    CapabilityRegistry,
    CapabilityRuntime,
    RepositoryCapability,
    WorkspaceCapability,
)
from eag.chief.runtime import ChiefRuntime, Coordinator, DefaultValidator
from eag.chief.runtime.planner import DefaultPlanner
from eag.events import EventBus
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import DefaultReflectionEngine, ReflectionRuntime
from eag.vcs.runtime import RepositoryRuntime
from eag.workspace.enums import WorkspaceMode
from eag.workspace.runtime import WorkspaceRuntime


@dataclass(frozen=True)
class AutonomousEngineeringComposition:
    """Publicly exposes the components assembled for an autonomous build."""

    loop: AutonomousLoopRuntime
    chief: ChiefRuntime
    coordinator: Coordinator
    capability_runtime: CapabilityRuntime
    memory_runtime: MemoryRuntime
    reflection_runtime: ReflectionRuntime
    workspace_runtime: WorkspaceRuntime
    repository_runtime: RepositoryRuntime
    event_bus: EventBus


def create_autonomous_engineering_composition(
    workspace_root: Path,
    *,
    event_bus: EventBus | None = None,
) -> AutonomousEngineeringComposition:
    """Build the one supported Gen1 autonomous engineering composition.

    This factory deliberately composes existing deterministic Gen1 services only.
    It does not enable LLM, review, worker, scheduler, or persistent-memory behavior.
    """

    root = workspace_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    bus = event_bus or EventBus()

    workspace_runtime = WorkspaceRuntime(root=root, mode=WorkspaceMode.LIVE, event_bus=bus)
    workspace_runtime.open()

    repository_runtime = RepositoryRuntime(root=root, event_bus=bus)
    repository_runtime.open()

    capability_registry = CapabilityRegistry()
    capability_registry.register(WorkspaceCapability(workspace_runtime))
    capability_registry.register(RepositoryCapability(repository_runtime))
    capability_runtime = CapabilityRuntime(registry=capability_registry)

    memory_runtime = MemoryRuntime(storage=InMemoryStorage(), event_bus=bus)
    reflection_runtime = ReflectionRuntime(engine=DefaultReflectionEngine(), event_bus=bus)

    base_planner = DefaultPlanner()
    adaptive_planner = AdaptivePlanner(base_planner=base_planner)
    coordinator = Coordinator(
        planner=base_planner,
        adaptive_planner=adaptive_planner,
        capability_runtime=capability_runtime,
        validator=DefaultValidator(),
        event_bus=bus,
        memory_runtime=memory_runtime,
    )
    chief = ChiefRuntime(event_bus=bus, coordinator=coordinator)
    loop = AutonomousLoopRuntime(
        chief_runtime=chief,
        reflection_runtime=reflection_runtime,
        memory_runtime=memory_runtime,
        event_bus=bus,
    )

    return AutonomousEngineeringComposition(
        loop=loop,
        chief=chief,
        coordinator=coordinator,
        capability_runtime=capability_runtime,
        memory_runtime=memory_runtime,
        reflection_runtime=reflection_runtime,
        workspace_runtime=workspace_runtime,
        repository_runtime=repository_runtime,
        event_bus=bus,
    )
