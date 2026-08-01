"""Task scheduler for EAG Chief Runtime."""

from eag.chief.runtime.enums import StepState
from eag.chief.runtime.errors import SchedulingError
from eag.chief.runtime.models import Plan, PlanStep


class TaskScheduler:
    """Schedules plan steps for execution, respecting dependencies."""

    def schedule(self, plan: Plan, completed_steps: set[str] | None = None) -> list[PlanStep]:
        """Returns steps ready to execute, sorted by dependencies."""
        completed = completed_steps or set()
        ready: list[PlanStep] = []
        
        for step in plan.steps:
            if step.step_id in completed:
                continue
            if step.state != StepState.PENDING:
                continue
            # Check if all dependencies are completed
            if all(dep in completed for dep in step.dependencies):
                ready.append(step)
                
        if not ready and not all(s.step_id in completed for s in plan.steps):
            raise SchedulingError("Deadlock: no steps ready but plan not complete.")
            
        return ready

    def get_next_step(self, plan: Plan, completed_steps: set[str] | None = None) -> PlanStep | None:
        """Returns the next step to execute, or None if plan is complete."""
        ready = self.schedule(plan, completed_steps)
        return ready[0] if ready else None

    def is_complete(self, plan: Plan, completed_steps: set[str]) -> bool:
        """Checks if all steps in the plan are completed."""
        return all(s.step_id in completed_steps for s in plan.steps)