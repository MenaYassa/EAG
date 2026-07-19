"""Engineering Risk Analyzer for EAG."""

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.intelligence.models import (
    EngineeringComplexity,
    EngineeringGoal,
    EngineeringOperation,
    EngineeringRiskAssessment,
    EngineeringRiskFactor,
    EngineeringScope,
    TaskDependencyGraph,
    TaskDependencyStatistics,
)


class RiskAnalyzer:
    """Evaluates engineering risk based on deterministic rules."""

    def analyze(
        self,
        goal: EngineeringGoal,
        graph: TaskDependencyGraph,
    ) -> EngineeringRiskAssessment:
        """Analyze the risk of an engineering goal and its task graph."""
        scope_risk = self._evaluate_scope(goal.scope)
        change_risk = self._evaluate_change(goal.operation)
        graph_risk = self._evaluate_graph(graph.statistics)
        dep_risk = self._evaluate_dependency(graph.statistics)

        factors = self._collect_factors(goal, graph)
        overall = self._aggregate([scope_risk, change_risk, graph_risk, dep_risk])
        approval = self._requires_approval(overall)
        rollback = self._evaluate_rollback(goal)
        summary = self._build_summary(goal, graph, overall, approval)
        confidence = 0.95 if goal.operation.name == "UPGRADE" else 1.0

        # Special Case check: if change risk is NONE, cap overall risk at the scope risk
        if change_risk == RiskLevel.NONE and overall > scope_risk:
            overall = scope_risk

        return EngineeringRiskAssessment(
            overall_risk=overall,
            confidence=confidence,
            scope_risk=scope_risk,
            change_risk=change_risk,
            graph_risk=graph_risk,
            dependency_risk=dep_risk,
            factors=factors,
            requires_approval=approval,
            rollback_complexity=rollback,
            summary=summary,
        )

    def _evaluate_scope(self, scope: EngineeringScope) -> RiskLevel:
        mapping = {
            "SYMBOL": RiskLevel.NONE,
            "FILE": RiskLevel.LOW,
            "MODULE": RiskLevel.LOW,
            "PACKAGE": RiskLevel.MEDIUM,
            "REPOSITORY": RiskLevel.HIGH,
            "SYSTEM": RiskLevel.CRITICAL,
        }
        return mapping.get(scope.name, RiskLevel.MEDIUM)

    def _evaluate_change(self, operation: EngineeringOperation) -> RiskLevel:
        mapping = {
            "ANALYZE": RiskLevel.NONE,
            "TEST": RiskLevel.NONE,
            "DOCUMENT": RiskLevel.LOW,
            "FIX": RiskLevel.LOW,
            "REFACTOR": RiskLevel.MEDIUM,
            "CREATE": RiskLevel.MEDIUM,
            "DELETE": RiskLevel.HIGH,
            "UPGRADE": RiskLevel.HIGH,
        }
        return mapping.get(operation.name, RiskLevel.MEDIUM)

    def _evaluate_graph(self, stats: TaskDependencyStatistics) -> RiskLevel:
        if stats.task_count <= 5:
            return RiskLevel.LOW
        if stats.task_count <= 20:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def _evaluate_dependency(self, stats: TaskDependencyStatistics) -> RiskLevel:
        if stats.maximum_depth <= 2:
            return RiskLevel.LOW
        if stats.maximum_depth <= 5:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def _collect_factors(
        self, goal: EngineeringGoal, graph: TaskDependencyGraph
    ) -> tuple[EngineeringRiskFactor, ...]:
        factors = []

        # Check scope risk factor
        if goal.scope.name in ["REPOSITORY", "SYSTEM"]:
            factors.append(EngineeringRiskFactor.LARGE_SCOPE)

        # Check dependency density
        if graph.statistics.task_count > 10:
            factors.append(EngineeringRiskFactor.MANY_DEPENDENCIES)

        # Check delete operations
        if goal.operation == EngineeringOperation.DELETE:
            factors.append(EngineeringRiskFactor.DELETE_OPERATION)

        # Fix: Both REFACTOR and RENAME map to the REFACTOR risk factor
        if goal.operation in (EngineeringOperation.REFACTOR, EngineeringOperation.RENAME):
            factors.append(EngineeringRiskFactor.REFACTOR)

        # Check goal type risk factors
        if goal.planning_goal.goal_type == GoalType.INFRASTRUCTURE:
            factors.append(EngineeringRiskFactor.INFRASTRUCTURE)

        # Check specialized operations
        if goal.operation == EngineeringOperation.TEST:
            factors.append(EngineeringRiskFactor.TESTING_ONLY)
        if goal.operation == EngineeringOperation.DOCUMENT:
            factors.append(EngineeringRiskFactor.DOCUMENTATION_ONLY)
        if goal.operation == EngineeringOperation.ANALYZE:
            factors.append(EngineeringRiskFactor.ANALYSIS_ONLY)

        return tuple(factors)

    def _aggregate(self, risks: list[RiskLevel]) -> RiskLevel:
        if RiskLevel.CRITICAL in risks:
            return RiskLevel.CRITICAL
        if RiskLevel.HIGH in risks:
            return RiskLevel.HIGH
        if risks.count(RiskLevel.MEDIUM) >= 3:
            return RiskLevel.HIGH
        if RiskLevel.MEDIUM in risks:
            return RiskLevel.MEDIUM
        if RiskLevel.LOW in risks:
            return RiskLevel.LOW
        return RiskLevel.NONE

    def _requires_approval(self, overall: RiskLevel) -> bool:
        return overall in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def _evaluate_rollback(self, goal: EngineeringGoal) -> EngineeringComplexity:
        if goal.operation.name == "DELETE":
            if goal.scope.name in ["SYMBOL", "FILE"]:
                return EngineeringComplexity.MEDIUM
            if goal.scope.name in ["MODULE", "PACKAGE"]:
                return EngineeringComplexity.HIGH
            return EngineeringComplexity.EXTREME

        mapping = {
            "ANALYZE": EngineeringComplexity.TRIVIAL,
            "DOCUMENT": EngineeringComplexity.TRIVIAL,
            "TEST": EngineeringComplexity.TRIVIAL,
            "FIX": EngineeringComplexity.LOW,
            "REFACTOR": EngineeringComplexity.MEDIUM,
            "CREATE": EngineeringComplexity.MEDIUM,
            "UPGRADE": EngineeringComplexity.HIGH,
        }
        return mapping.get(goal.operation.name, EngineeringComplexity.MEDIUM)

    def _build_summary(
        self,
        goal: EngineeringGoal,
        graph: TaskDependencyGraph,
        overall: RiskLevel,
        approval: bool,
    ) -> str:
        scope_str = goal.scope.name.capitalize()
        op_str = goal.operation.name.lower()
        task_count = graph.statistics.task_count
        approval_str = " Manual approval required." if approval else ""
        return f"{scope_str}-wide {op_str} affecting {task_count} engineering tasks.{approval_str}"
