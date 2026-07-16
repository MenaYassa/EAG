"""Engineering operation protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.planner.intelligence.models import EngineeringGoal
from eag.planner.models import EngineeringTask
from eag.planner.operations.models import EngineeringOperationDefinition


@runtime_checkable
class EngineeringOperation(Protocol):
    """The contract for a reusable engineering operation."""

    @property
    def definition(self) -> EngineeringOperationDefinition:
        """Returns metadata about this operation."""
        ...

    def supports(self, goal: EngineeringGoal) -> bool:
        """Check if this operation can handle the given engineering goal."""
        ...

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        """Generate the engineering tasks required to fulfill the goal."""
        ...

    def estimate(self, goal: EngineeringGoal) -> float:
        """Estimate the duration of this operation in minutes."""
        ...

    def explain(self) -> str:
        """Provide a human-readable explanation of this operation."""
        ...