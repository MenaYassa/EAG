"""Task Decomposer for EAG.

Converts an EngineeringGoal into a deterministic list of EngineeringTasks
using reusable engineering templates.
"""

from eag.planner.intelligence.models import EngineeringGoal, EngineeringOperation
from eag.planner.models import EngineeringTask
from eag.planner.intelligence.models import EngineeringGoal

from eag.planner.operations import OperationRegistry, default_operation_registry

class TaskDecomposer:
    """Decomposes an engineering goal into actionable engineering tasks."""

    _TEMPLATES: dict[EngineeringOperation, list[str]] = {
        EngineeringOperation.REFACTOR: [
            "Locate Target",
            "Analyze Dependencies",
            "Modify Code",
            "Update References",
            "Run Validation",
        ],
        EngineeringOperation.RENAME: [
            "Locate Target",
            "Analyze References",
            "Rename Declaration",
            "Update References",
            "Validate Repository",
        ],
        EngineeringOperation.FIX: [
            "Reproduce Problem",
            "Locate Cause",
            "Implement Fix",
            "Run Tests",
            "Verify Fix",
        ],
        EngineeringOperation.CREATE: [
            "Analyze Requirement",
            "Design Change",
            "Implement",
            "Test",
            "Document",
        ],
        EngineeringOperation.DOCUMENT: [
            "Analyze Existing Docs",
            "Update Documentation",
            "Review Consistency",
        ],
        EngineeringOperation.ANALYZE: [
            "Define Scope",
            "Gather Data",
            "Analyze",
            "Report Findings",
        ],
        EngineeringOperation.DELETE: [
            "Identify Target",
            "Check Dependencies",
            "Remove Code",
            "Run Validation",
        ],
        EngineeringOperation.EXTRACT: [
            "Locate Target",
            "Create New Module",
            "Move Code",
            "Update Imports",
            "Run Validation",
        ],
        EngineeringOperation.MOVE: [
            "Identify Target",
            "Determine Destination",
            "Move Code",
            "Update Imports",
            "Run Validation",
        ],
        EngineeringOperation.TEST: [
            "Identify Target",
            "Write Tests",
            "Run Tests",
            "Verify Coverage",
        ],
        EngineeringOperation.UPGRADE: [
            "Identify Target Version",
            "Check Breaking Changes",
            "Upgrade Dependency",
            "Fix Breaking Changes",
            "Run Validation",
        ],
    }
    def __init__(self, registry: OperationRegistry | None = None) -> None:
        self._registry = registry or default_operation_registry()
      
    def decompose(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        """Convert an EngineeringGoal into a tuple of EngineeringTasks."""
        try:
            operation = self._registry.find(goal)
        except Exception as e:
            # Catch the registry exception and raise the ValueError expected by the unit tests
            raise ValueError(f"No decomposition template found for goal: {goal}") from e
            
        return operation.generate_tasks(goal)



    def _select_template(self, operation: EngineeringOperation) -> list[str]:
        if operation not in self._TEMPLATES:
            raise ValueError(f"No decomposition template found for operation: {operation}")
        return self._TEMPLATES[operation]

    def _build_tasks(self, template: list[str]) -> list[EngineeringTask]:
        tasks: list[EngineeringTask] = []
        for i, title in enumerate(template, start=1):
            task_id = f"TASK-{i:03d}"
            deps = (f"TASK-{i - 1:03d}",) if i > 1 else ()
            tasks.append(
                EngineeringTask(
                    id=task_id,
                    title=title,
                    dependencies=deps,
                )
            )
        return tasks

    def _validate(self, tasks: list[EngineeringTask]) -> None:
        if not tasks:
            raise ValueError("Decomposition resulted in empty task list.")
        ids = [t.id for t in tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate task IDs detected.")


