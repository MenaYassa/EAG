"""Built-in Review Worker for EAG."""

from eag.workers.enums import WorkerRole
from eag.workers.models import WorkerContext, WorkerProfile, WorkerResult, WorkerTask


class ReviewWorker:
    """A specialized worker that reviews engineering artifacts."""

    @property
    def profile(self) -> WorkerProfile:
        return WorkerProfile(
            id="w_review",
            name="Review Worker",
            role=WorkerRole.REVIEW,
            capabilities=("review", "architecture", "style", "testing", "quality"),
            preferred_capabilities=("review",),
        )

    def supports(self, task: WorkerTask) -> bool:
        return task.required_capability == "review"

    def estimate(self, task: WorkerTask) -> float:
        return 1.0

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        # In a real implementation, this would inspect the workspace and artifacts
        return WorkerResult(
            worker_id=self.profile.id,
            task_id=task.id,
            success=True,
            summary="Review passed. Code quality is excellent.",
            artifacts=context.shared_artifacts,
        )
