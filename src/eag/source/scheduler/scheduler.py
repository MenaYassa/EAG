"""Transformation scheduler for EAG."""

import heapq
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from eag.source.python import Transformation, TransformationContext, TransformationResult
from eag.source.runtime import SourceRuntime


@dataclass(order=True)
class ScheduledTask:
    priority: int
    seq: int
    transformation: Transformation = field(compare=False)
    context: TransformationContext = field(compare=False)
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    dependencies: tuple[str, ...] = field(default_factory=tuple, compare=False)


class TransformationScheduler:
    """Queues and executes transformations respecting priority and dependencies."""

    def __init__(self, runtime: SourceRuntime) -> None:
        self._runtime = runtime
        self._queue: list[ScheduledTask] = []
        self._completed: set[str] = set()
        self._state: dict[Path, tuple[str, Any]] = {}  # path -> (content, document)
        self._seq = 0

    def submit(
        self,
        transformation: Transformation,
        context: TransformationContext,
        priority: int = 0,
        dependencies: tuple[str, ...] = (),
    ) -> str:
        path = context.document.path
        if path not in self._state:
            self._state[path] = (context.content, context.document)

        self._seq += 1
        task = ScheduledTask(
            priority=priority,
            seq=self._seq,
            transformation=transformation,
            context=context,
            dependencies=dependencies,
        )
        heapq.heappush(self._queue, task)
        return task.task_id

    def execute(self) -> list[TransformationResult]:
        results: list[TransformationResult] = []

        while self._queue:
            # Find the next task whose dependencies are met
            ready_task_idx = -1
            for i, task in enumerate(self._queue):
                if all(dep in self._completed for dep in task.dependencies):
                    ready_task_idx = i
                    break

            if ready_task_idx == -1:
                # No tasks are ready (deadlock or waiting)
                break

            # Pop the highest priority ready task
            task = self._queue.pop(ready_task_idx)
            heapq.heapify(self._queue)  # Re-heapify after removal

            # Reconstruct context with the latest accumulated state
            path = task.context.document.path
            current_content, current_doc = self._state.get(
                path, (task.context.content, task.context.document)
            )
            current_ctx = replace(task.context, document=current_doc, content=current_content)

            result = task.transformation.apply(current_ctx)
            results.append(result)
            self._completed.add(task.task_id)

            # If successful, update the state for the next task
            if result.success and result.edits:
                new_content = result.edits[0].new_content
                new_doc = self._runtime.parse(path, new_content)
                self._state[path] = (new_content, new_doc)

        return results
