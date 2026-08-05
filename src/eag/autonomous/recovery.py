"""Recovery Engine for EAG Autonomous Loop."""

from eag.autonomous.enums import RecoveryActionType, RecoveryPolicy
from eag.autonomous.models import LoopDecision, RecoveryAction
from eag.chief.runtime.models import RunResult


class RecoveryEngine:
    """Evaluates failures and determines the concrete recovery action."""

    def evaluate(self, run_result: RunResult, decision: LoopDecision) -> RecoveryAction:
        """Translates a LoopDecision's recovery policy into a concrete action."""

        if decision.recovery_policy == RecoveryPolicy.ABORT:
            return RecoveryAction(
                action_type=RecoveryActionType.ABORT,
                reason="Aborting loop due to critical failure or max retries.",
            )

        if decision.recovery_policy == RecoveryPolicy.RETRY:
            return RecoveryAction(
                action_type=RecoveryActionType.RETRY, reason="Retrying the same plan."
            )

        if decision.recovery_policy == RecoveryPolicy.DIFFERENT_WORKER:
            # In a real system, we'd inspect run_result to find the failed worker
            failed_worker_id = "w_unknown"
            if hasattr(run_result, "step_results"):
                for step in run_result.step_results:
                    if not step.success:
                        failed_worker_id = step.metadata.get("worker_id", failed_worker_id)
                        break

            return RecoveryAction(
                action_type=RecoveryActionType.EXCLUDE_WORKER,
                target_worker_id=failed_worker_id,
                reason=f"Excluding failed worker {failed_worker_id} and retrying.",
            )

        if decision.recovery_policy == RecoveryPolicy.DIFFERENT_CAPABILITY:
            return RecoveryAction(
                action_type=RecoveryActionType.CHANGE_CAPABILITY,
                new_capability="fallback_capability",
                reason="Switching to fallback capability.",
            )

        if decision.recovery_policy == RecoveryPolicy.DIFFERENT_STRATEGY:
            return RecoveryAction(
                action_type=RecoveryActionType.CHANGE_STRATEGY,
                new_strategy="conservative",
                reason="Switching to conservative planning strategy.",
            )

        # Default to retry
        return RecoveryAction(action_type=RecoveryActionType.RETRY, reason="Defaulting to retry.")
