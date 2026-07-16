"""Built-in engineering operations for EAG."""

from eag.planner.intelligence.models import EngineeringGoal, EngineeringOperation as EngOpEnum
from eag.planner.models import EngineeringTask
from eag.planner.operations.enums import (
    OperationCategory,
    OperationComplexity,
    OperationSafety,
)
from eag.planner.operations.models import EngineeringOperationDefinition
from eag.planner.operations.protocol import EngineeringOperation


class _BaseOperation:
    """Base class providing default implementations for operations."""
    
    _definition: EngineeringOperationDefinition

    @property
    def definition(self) -> EngineeringOperationDefinition:
        return self._definition

    def supports(self, goal: EngineeringGoal) -> bool:
        raise NotImplementedError

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        raise NotImplementedError

    def estimate(self, goal: EngineeringGoal) -> float:
        return self._definition.estimated_minutes

    def explain(self) -> str:
        return f"{self._definition.name}: {self._definition.description}"


def _make_tasks(titles: list[str]) -> tuple[EngineeringTask, ...]:
    tasks = []
    for i, title in enumerate(titles, start=1):
        task_id = f"TASK-{i:03d}"
        deps = (f"TASK-{i-1:03d}",) if i > 1 else ()
        tasks.append(EngineeringTask(id=task_id, title=title, dependencies=deps))
    return tuple(tasks)


class RenameSymbolOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="rename_symbol",
            name="Rename Symbol",
            description="Renames a symbol and updates all references.",
            category=OperationCategory.REFACTORING,
            complexity=OperationComplexity.LOW,
            safety=OperationSafety.CAUTION,
            estimated_minutes=4.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.RENAME

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Locate Symbol",
            "Analyze References",
            "Rename Declaration",
            "Update References",
            "Validate Repository",
        ])


class RefactorOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="refactor",
            name="Refactor",
            description="General code refactoring workflow.",
            category=OperationCategory.REFACTORING,
            complexity=OperationComplexity.MEDIUM,
            safety=OperationSafety.CAUTION,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.REFACTOR

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Locate Target",
            "Analyze Dependencies",
            "Modify Code",
            "Update References",
            "Run Validation",
        ])


class FixBugOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="fix_bug",
            name="Fix Bug",
            description="Diagnoses and fixes a bug.",
            category=OperationCategory.CODE,
            complexity=OperationComplexity.LOW,
            safety=OperationSafety.SAFE,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.FIX

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Reproduce Problem",
            "Locate Cause",
            "Implement Fix",
            "Run Tests",
            "Verify Fix",
        ])


class CreateFeatureOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="create_feature",
            name="Create Feature",
            description="Implements a new feature.",
            category=OperationCategory.CODE,
            complexity=OperationComplexity.MEDIUM,
            safety=OperationSafety.SAFE,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.CREATE

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Analyze Requirement",
            "Design Change",
            "Implement",
            "Test",
            "Document",
        ])


class DocumentOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="document",
            name="Document",
            description="Updates or creates documentation.",
            category=OperationCategory.DOCUMENTATION,
            complexity=OperationComplexity.TRIVIAL,
            safety=OperationSafety.SAFE,
            estimated_minutes=3.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.DOCUMENT

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Analyze Existing Docs",
            "Update Documentation",
            "Review Consistency",
        ])


class AnalyzeOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="analyze",
            name="Analyze",
            description="Analyzes code or architecture.",
            category=OperationCategory.ANALYSIS,
            complexity=OperationComplexity.TRIVIAL,
            safety=OperationSafety.SAFE,
            estimated_minutes=4.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.ANALYZE

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Define Scope",
            "Gather Data",
            "Analyze",
            "Report Findings",
        ])


class DeleteOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="delete",
            name="Delete",
            description="Removes code or files safely.",
            category=OperationCategory.CODE,
            complexity=OperationComplexity.LOW,
            safety=OperationSafety.DANGEROUS,
            estimated_minutes=4.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.DELETE

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Identify Target",
            "Check Dependencies",
            "Remove Code",
            "Run Validation",
        ])


class ExtractOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="extract",
            name="Extract",
            description="Extracts code into a new module or file.",
            category=OperationCategory.REFACTORING,
            complexity=OperationComplexity.MEDIUM,
            safety=OperationSafety.CAUTION,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.EXTRACT

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Locate Target",
            "Create New Module",
            "Move Code",
            "Update Imports",
            "Run Validation",
        ])


class MoveOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="move",
            name="Move",
            description="Moves code or files.",
            category=OperationCategory.FILESYSTEM,
            complexity=OperationComplexity.LOW,
            safety=OperationSafety.CAUTION,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.MOVE

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Identify Target",
            "Determine Destination",
            "Move Code",
            "Update Imports",
            "Run Validation",
        ])


class RunTestsOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="run_tests",
            name="Run Tests",
            description="Writes or updates tests.",
            category=OperationCategory.TESTING,
            complexity=OperationComplexity.LOW,
            safety=OperationSafety.SAFE,
            estimated_minutes=4.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.TEST

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Identify Target",
            "Write Tests",
            "Run Tests",
            "Verify Coverage",
        ])


class UpgradeOperation(_BaseOperation):
    def __init__(self) -> None:
        self._definition = EngineeringOperationDefinition(
            id="upgrade",
            name="Upgrade",
            description="Upgrades dependencies or infrastructure.",
            category=OperationCategory.REPOSITORY,
            complexity=OperationComplexity.HIGH,
            safety=OperationSafety.DANGEROUS,
            estimated_minutes=5.0,
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.operation == EngOpEnum.UPGRADE

    def generate_tasks(self, goal: EngineeringGoal) -> tuple[EngineeringTask, ...]:
        return _make_tasks([
            "Identify Target Version",
            "Check Breaking Changes",
            "Upgrade Dependency",
            "Fix Breaking Changes",
            "Run Validation",
        ])


def default_operation_registry() -> "OperationRegistry":
    """Returns a registry populated with all built-in operations."""
    from eag.planner.operations.registry import OperationRegistry
    
    registry = OperationRegistry()
    ops = [
        RenameSymbolOperation(),
        RefactorOperation(),
        FixBugOperation(),
        CreateFeatureOperation(),
        DocumentOperation(),
        AnalyzeOperation(),
        DeleteOperation(),
        ExtractOperation(),
        MoveOperation(),
        RunTestsOperation(),
        UpgradeOperation(),
    ]
    for op in ops:
        registry.register(op)
    return registry