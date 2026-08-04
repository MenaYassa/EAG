"""Parallel Execution Graph Platform for EAG."""

from eag.execution_graph.enums import FailurePolicy, MessageType, NodeState
from eag.execution_graph.errors import (
    CycleError,
    DuplicateNodeError,
    ExecutionGraphError,
    MissingNodeError,
)
from eag.execution_graph.executor import BatchExecutor, BatchResult
from eag.execution_graph.graph import ArtifactGraph, ExecutionGraph
from eag.execution_graph.messaging import Mailbox, MessageRouter
from eag.execution_graph.metrics import ExecutionMetrics
from eag.execution_graph.models import (
    ArtifactEdge,
    ArtifactNode,
    ExecutionEdge,
    ExecutionNode,
    WorkerMessage,
)
from eag.execution_graph.runtime import ParallelExecutionRuntime

__all__ = [
    # Enums
    "FailurePolicy",
    "MessageType",
    "NodeState",
    # Errors
    "CycleError",
    "DuplicateNodeError",
    "ExecutionGraphError",
    "MissingNodeError",
    # Models
    "ArtifactEdge",
    "ArtifactNode",
    "ExecutionEdge",
    "ExecutionNode",
    "WorkerMessage",
    # Graph
    "ArtifactGraph",
    "ExecutionGraph",
    # Messaging
    "Mailbox",
    "MessageRouter",
    # Executor
    "BatchExecutor",
    "BatchResult",
    # Runtime
    "ParallelExecutionRuntime",
    # Metrics
    "ExecutionMetrics",
]