"""Goal Analyzer for EAG.

Converts a PlanningGoal into an EngineeringGoal using deterministic rules.
"""

from eag.planner.enums import GoalType
from eag.planner.intelligence.models import (
    EngineeringComplexity,
    EngineeringGoal,
    EngineeringOperation,
    EngineeringScope,
)
from eag.planner.models import PlanningGoal


class GoalAnalyzer:
    """Analyzes user-facing goals and translates them into engineering operations."""

    def analyze(self, goal: PlanningGoal) -> EngineeringGoal:
        """Convert a PlanningGoal into a deterministic EngineeringGoal."""
        self._validate(goal)
        operation = self._classify_operation(goal)
        target = self._identify_target(goal)
        complexity = self._estimate_complexity(goal)
        scope = self._estimate_scope(goal)
        return self._build_goal(goal, operation, target, complexity, scope)

    def _validate(self, goal: PlanningGoal) -> None:
        if not isinstance(goal, PlanningGoal):
            raise TypeError("Goal must be a PlanningGoal instance.")
        if not goal.title.strip():
            raise ValueError("Goal title cannot be empty.")

    def _classify_operation(self, goal: PlanningGoal) -> EngineeringOperation:
        """Map GoalType to a deterministic EngineeringOperation."""
        mapping = {
            GoalType.ANALYSIS: EngineeringOperation.ANALYZE,
            GoalType.BUGFIX: EngineeringOperation.FIX,
            GoalType.DOCUMENTATION: EngineeringOperation.DOCUMENT,
            GoalType.FEATURE: EngineeringOperation.CREATE,
            GoalType.INFRASTRUCTURE: EngineeringOperation.UPGRADE,
            GoalType.MAINTENANCE: EngineeringOperation.REFACTOR,
            GoalType.REFACTOR: EngineeringOperation.REFACTOR,
            GoalType.TESTING: EngineeringOperation.TEST,
        }
        return mapping.get(goal.goal_type, EngineeringOperation.ANALYZE)

    def _identify_target(self, goal: PlanningGoal) -> str:
        """Extract the target of the operation.

        Version 1: Simply use the title as the target string.
        Later versions may use NLP or symbols to extract precise targets.
        """
        return goal.title

    def _estimate_complexity(self, goal: PlanningGoal) -> EngineeringComplexity:
        """Map GoalType to a deterministic complexity level."""
        mapping = {
            GoalType.ANALYSIS: EngineeringComplexity.TRIVIAL,
            GoalType.BUGFIX: EngineeringComplexity.LOW,
            GoalType.DOCUMENTATION: EngineeringComplexity.LOW,
            GoalType.FEATURE: EngineeringComplexity.MEDIUM,
            GoalType.MAINTENANCE: EngineeringComplexity.MEDIUM,
            GoalType.REFACTOR: EngineeringComplexity.MEDIUM,
            GoalType.TESTING: EngineeringComplexity.LOW,
            GoalType.INFRASTRUCTURE: EngineeringComplexity.HIGH,
        }
        return mapping.get(goal.goal_type, EngineeringComplexity.MEDIUM)

    def _estimate_scope(self, goal: PlanningGoal) -> EngineeringScope:
        """Map GoalType to a deterministic engineering scope."""
        mapping = {
            GoalType.ANALYSIS: EngineeringScope.FILE,
            GoalType.BUGFIX: EngineeringScope.FILE,
            GoalType.DOCUMENTATION: EngineeringScope.PACKAGE,
            GoalType.FEATURE: EngineeringScope.MODULE,
            GoalType.MAINTENANCE: EngineeringScope.PACKAGE,
            GoalType.REFACTOR: EngineeringScope.REPOSITORY,
            GoalType.TESTING: EngineeringScope.FILE,
            GoalType.INFRASTRUCTURE: EngineeringScope.SYSTEM,
        }
        return mapping.get(goal.goal_type, EngineeringScope.REPOSITORY)

    def _build_goal(
        self,
        goal: PlanningGoal,
        operation: EngineeringOperation,
        target: str,
        complexity: EngineeringComplexity,
        scope: EngineeringScope,
    ) -> EngineeringGoal:
        return EngineeringGoal(
            planning_goal=goal,
            operation=operation,
            target=target,
            complexity=complexity,
            scope=scope,
            confidence=1.0,  # Deterministic rules have perfect confidence
        )
