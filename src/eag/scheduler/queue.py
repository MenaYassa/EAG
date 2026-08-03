"""Ready Queue for EAG Scheduler."""

from eag.scheduler.errors import QueueError
from eag.task_graph.models import TaskNode
from eag.workers.enums import TaskPriority


class ReadyQueue:
    """A priority queue for ready tasks."""

    def __init__(self) -> None:
        self._queue: list[TaskNode] = []

    def push(self, task: TaskNode) -> None:
        """Pushes a task to the queue, maintaining priority order."""
        if self.contains(task.id):
            raise QueueError(f"Task '{task.id}' is already in the queue")
            
        self._queue.append(task)
        # Sort by priority (descending) and then ID for determinism
        priority_order = {
            "critical": 0,
            "high": 1,
            "normal": 2,
            "low": 3
        }
        self._queue.sort(key=lambda t: (priority_order.get(t.priority.value, 2), t.id))

    def pop(self) -> TaskNode:
        """Pops the highest priority task."""
        if not self._queue:
            raise QueueError("Queue is empty")
        return self._queue.pop(0)

    def peek(self) -> TaskNode:
        """Peeks at the highest priority task without removing it."""
        if not self._queue:
            raise QueueError("Queue is empty")
        return self._queue[0]

    def remove(self, task_id: str) -> bool:
        """Removes a task by ID."""
        for i, task in enumerate(self._queue):
            if task.id == task_id:
                self._queue.pop(i)
                return True
        return False

    def clear(self) -> None:
        self._queue.clear()

    def contains(self, task_id: str) -> bool:
        return any(t.id == task_id for t in self._queue)

    def size(self) -> int:
        return len(self._queue)

    def empty(self) -> bool:
        return len(self._queue) == 0
