"""Engineering operation registry for EAG."""

from eag.planner.errors import PlannerError
from eag.planner.intelligence.models import EngineeringGoal
from eag.planner.operations.protocol import EngineeringOperation


class OperationRegistry:
    """Discovers and manages available engineering operations."""

    def __init__(self) -> None:
        self._operations: dict[str, EngineeringOperation] = {}

    def register(self, operation: EngineeringOperation) -> None:
        op_id = operation.definition.id
        if op_id in self._operations:
            raise PlannerError(f"Operation '{op_id}' is already registered.")
        self._operations[op_id] = operation

    def unregister(self, op_id: str) -> bool:
        if op_id in self._operations:
            del self._operations[op_id]
            return True
        return False

    def find(self, goal: EngineeringGoal) -> EngineeringOperation:
        """Find the first registered operation that supports the given goal."""
        for op in self._operations.values():
            if op.supports(goal):
                return op
        raise PlannerError(f"No operation supports engineering goal: {goal.operation}")

    def find_all(self, goal: EngineeringGoal) -> tuple[EngineeringOperation, ...]:
        """Find all registered operations that support the given goal."""
        return tuple(op for op in self._operations.values() if op.supports(goal))

    def list(self) -> tuple[EngineeringOperation, ...]:
        """Return all registered operations."""
        return tuple(self._operations.values())

    def categories(self) -> tuple[str, ...]:
        """Return a sorted tuple of all registered operation categories."""
        return tuple(sorted({op.definition.category.value for op in self._operations.values()}))

    def count(self) -> int:
        return len(self._operations)

    def default(self) -> EngineeringOperation:
        """Return the first registered operation (fallback)."""
        if not self._operations:
            raise PlannerError("No operations registered.")
        return next(iter(self._operations.values()))
