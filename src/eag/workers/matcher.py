"""Capability matcher for EAG Worker Collaboration."""

from dataclasses import dataclass

from eag.workers.models import WorkerTask
from eag.workers.protocol import Worker


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityScore:
    """The explainable result of scoring a worker against a task."""

    worker_id: str
    score: float = 0.0
    matched_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class CapabilityMatcher:
    """Scores and ranks workers based on task requirements."""

    def score(self, worker: Worker, task: WorkerTask) -> CapabilityScore:
        """Scores a single worker for a specific task."""
        reasons: list[str] = []
        matched: list[str] = []
        missing: list[str] = []
        score = 0.0

        req_cap = task.required_capability

        if not req_cap:
            # If no specific capability required, any worker can do it
            score = 50.0
            reasons.append("No specific capability required")
        else:
            if req_cap in worker.profile.capabilities:
                score = 80.0
                matched.append(req_cap)
                reasons.append(f"Has required capability: {req_cap}")

                if req_cap in worker.profile.preferred_capabilities:
                    score += 20.0
                    reasons.append(f"Prefers this capability: {req_cap}")

                if worker.profile.role.value == req_cap:
                    score += 10.0
                    reasons.append(f"Role matches capability: {req_cap}")
            else:
                missing.append(req_cap)
                reasons.append(f"Missing required capability: {req_cap}")
                score = 0.0

        # Cap at 100
        score = min(100.0, score)

        return CapabilityScore(
            worker_id=worker.profile.id,
            score=score,
            matched_capabilities=tuple(matched),
            missing_capabilities=tuple(missing),
            reasons=tuple(reasons),
        )

    def rank(self, workers: tuple[Worker, ...], task: WorkerTask) -> tuple[CapabilityScore, ...]:
        """Ranks all workers for a task, filtering out those who lack required capabilities."""
        scores = [self.score(w, task) for w in workers]

        # Filter out workers who are missing required capabilities
        if task.required_capability:
            scores = [s for s in scores if s.score > 0]

        # Sort by score descending, then by worker_id for determinism
        scores.sort(key=lambda s: (-s.score, s.worker_id))
        return tuple(scores)

    def best_worker(
        self, workers: tuple[Worker, ...], task: WorkerTask
    ) -> tuple[Worker, CapabilityScore] | None:
        """Finds the best worker for a task and returns them along with their score."""
        ranked = self.rank(workers, task)
        if not ranked:
            return None

        best_score = ranked[0]
        for w in workers:
            if w.profile.id == best_score.worker_id:
                return w, best_score

        return None
