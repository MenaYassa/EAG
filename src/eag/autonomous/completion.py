"""Completion Engine for EAG Autonomous Loop."""

from eag.autonomous.enums import CompletionAction, RecoveryPolicy
from eag.autonomous.models import LoopDecision
from eag.chief.runtime.models import RunResult
from eag.reflection.models import ReflectionReport


class CompletionEngine:
    """Evaluates whether the engineering objective is satisfied."""

    def evaluate(
        self,
        run_result: RunResult,
        reflection: ReflectionReport,
        iteration: int,
        max_iterations: int,
    ) -> LoopDecision:
        """Determines the next action for the loop."""

        # 1. Check for hard failure
        if run_result.outcome == "failure":
            if iteration >= max_iterations:
                return LoopDecision(
                    continue_loop=False,
                    reason="Max iterations reached after failure.",
                    action=CompletionAction.ESCALATE,
                    recovery_policy=RecoveryPolicy.ABORT,
                    confidence=1.0,
                )
            return LoopDecision(
                continue_loop=True,
                reason="Execution failed. Attempting recovery.",
                action=CompletionAction.REPLAN,
                recovery_policy=RecoveryPolicy.RETRY,
                confidence=0.8,
            )

        # 2. Check review score
        review_score = reflection.metrics.review_score
        if review_score < 80:
            if iteration >= max_iterations:
                return LoopDecision(
                    continue_loop=False,
                    reason="Max iterations reached. Review score still below threshold.",
                    action=CompletionAction.ESCALATE,
                    confidence=1.0,
                )
            return LoopDecision(
                continue_loop=True,
                reason=f"Review score {review_score} is below 80. Needs improvement.",
                action=CompletionAction.CONTINUE,
                recovery_policy=RecoveryPolicy.DIFFERENT_STRATEGY,
                confidence=0.9,
                expected_improvement=0.1,  # <-- FIXED: 10.0 converted to 0.1
            )

        # 3. Check for critical findings
        critical_findings = [f for f in reflection.findings if f.severity.value == "critical"]
        if critical_findings:
            return LoopDecision(
                continue_loop=False,
                reason="Critical issues detected in reflection.",
                action=CompletionAction.ESCALATE,
                recovery_policy=RecoveryPolicy.ABORT,
                confidence=1.0,
            )

        # 4. Success
        return LoopDecision(
            continue_loop=False,
            reason="Engineering objective satisfied. Review score is acceptable.",
            action=CompletionAction.STOP,
            confidence=1.0,
        )
