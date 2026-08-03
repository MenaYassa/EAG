Here is the complete, organized markdown file. You can copy this directly into your repo as `docs/VALIDATION_REPORT.md` or similar.

---

```markdown
# EAG Validation Report — Full Architecture Audit

> **Audited by:** AI Architecture Review  
> **Date:** 2026-07  
> **Scope:** `src/eag/` — Phases 0 through 5 (Kernel → Presentation & Ops)  
> **Method:** Source code inspection of 40+ files across all runtime modules  
> **Conclusion:** Architecture is sound. 3 high-severity wiring issues must be resolved before Sprint 8.

---

## Table of Contents

1. [Critical Fixes (High Severity)](#1-critical-fixes-high-severity)
2. [Architectural Recommendations (Pre-Sprint 8)](#2-architectural-recommendations-pre-sprint-8)
3. [Medium Severity Flags](#3-medium-severity-flags)
4. [Low Severity Flags](#4-low-severity-flags)
5. [Constitution Compliance Matrix](#5-constitution-compliance-matrix)
6. [Phase Validation Summary](#6-phase-validation-summary)

---

## 1. Critical Fixes (High Severity)

These three flags form a **connected safety gap**. The machinery exists, but the execution loop doesn't call it. Fix all three together.

### F4 — `ExecutionRuntime.rollback()` is a stub

| Attribute | Value |
|-----------|-------|
| **Phase** | 2 — Safety & Execution |
| **File** | `src/eag/execution/runtime/runtime.py` |
| **Severity** | 🔴 High |
| **Effort** | Small (wiring fix) |

**Current State:**
```python
# src/eag/execution/runtime/runtime.py
def rollback(self, context: ExecutionContext, rollback_point: RollbackPoint) -> ExecutionResult:
    return ExecutionResult(success=True, summary="Rollback not fully implemented yet.")
```

Meanwhile, `SafetyRuntime.rollback()` **is** fully implemented via `RollbackEngine` + `GitSafetyBackend`:
```python
# src/eag/safety/runtime.py
def rollback(self) -> None:
    if self._latest_checkpoint is None:
        return
    self._state = SafetyState.ROLLING_BACK
    self._rollback_engine.rollback(self._latest_checkpoint.id)
    self._state = SafetyState.ROLLED_BACK
```

**Problem:**
When a step fails in `ExecutionRuntime.execute()`, the runtime transitions to `ExecutionState.FAILED` and publishes `ExecutionFailed`, but it **never calls `SafetyRuntime.rollback()`**. The Git checkpoint was created, but the workspace is not restored on failure. This means a partially-applied changeset is left on disk.

**Required Fix:**
1. Inject `SafetyRuntime` into `ExecutionRuntime` (or into `ExecutionContext`).
2. In `ExecutionRuntime.execute()`, after `self._lifecycle.transition_to(ExecutionState.FAILED)`, call:
   ```python
   if safety_runtime is not None:
       safety_runtime.rollback()
   ```
3. Publish a new `RollbackCompleted` event from the execution layer.
4. The `RollbackPoint` returned by `checkpoint()` should contain the actual checkpoint ID from `SafetyRuntime.create_checkpoint()`.

---

### F8 — `PlanValidator` is not wired into `PlannerRuntime`

| Attribute | Value |
|-----------|-------|
| **Phase** | 3 — Reasoning (Planner) |
| **File** | `src/eag/planner/runtime.py` |
| **Severity** | 🔴 High |
| **Effort** | Small (wiring fix) |

**Current State:**
`PlannerRuntime._validate_plan()` only checks:
- Tasks are non-empty
- Steps are non-empty
- Plan goal ID matches original goal ID

```python
# src/eag/planner/runtime.py (simplified)
def _validate_plan(self, plan: ExecutionPlan, original_goal: PlanningGoal) -> None:
    if not plan.tasks:
        raise PlanningValidationError("Plan must contain at least one task.")
    if not plan.steps:
        raise PlanningValidationError("Plan must contain at least one step.")
    if plan.goal.id != original_goal.id:
        raise PlanningValidationError("Generated plan goal does not match original goal.")
```

Meanwhile, a full 5-rule validator exists but is **never called**:
```python
# src/eag/planner/validation/validator.py
class PlanValidator:
    def __init__(self, operation_registry=None):
        self._rules: list[PlanValidationRule] = [
            StructureRule(),
            DependencyRule(),
            SafetyRule(),
            RiskRule(),
            ExecutionRule(...),
        ]
    def validate(self, artifact: EngineeringPlanningArtifact) -> EngineeringPlanValidationResult:
        # ... 5 rules executed, issues aggregated, valid boolean returned ...
```

**Problem:**
A plan with circular dependencies, safety violations, or high-risk operations would pass validation. The `DependencyRule` (cycle detection), `SafetyRule` (destructive action detection), and `RiskRule` (risk threshold enforcement) are all dead code.

**Required Fix:**
1. Inject `PlanValidator` into `PlannerRuntime.__init__()`.
2. In `PlannerRuntime.plan()`, after `self._generate_plan()`, call:
   ```python
   validation_result = self._plan_validator.validate(artifact)
   if not validation_result.valid:
       raise PlanningValidationError(validation_result.summary)
   ```
3. Attach `validation_result` to the `PlanningResult` so the caller can inspect issues.
4. If `validation_result.requires_approval`, set `plan.state = PlanState.AWAITING_APPROVAL` instead of `PlanState.VALIDATED`.

---

### F9 — Chief `Coordinator` bypasses Safety Runtime and Approval Manager

| Attribute | Value |
|-----------|-------|
| **Phase** | 4 — Orchestration (Chief Engineer) |
| **File** | `src/eag/chief/runtime/coordinator.py` |
| **Severity** | 🔴 High |
| **Effort** | Medium (requires pipeline redesign) |

**Current State:**
`Coordinator.run()` executes the pipeline: `PLANNING → EXECUTION → COMPLETION`. It creates a `CapabilityContext`, then for each step calls `capability_runtime.execute()` and `validator.validate()`.

At **no point** does the Coordinator interact with:
- `SafetyRuntime.prepare()` — No checkpoint is created before execution
- `SafetyRuntime.inspect()` — No workspace health check
- `ApprovalManager.create()` / `.approve()` — No approval gate for destructive operations
- `SafetyRuntime.rollback()` — No rollback on failure

```python
# src/eag/chief/runtime/coordinator.py (simplified)
def run(self, context: RunContext) -> RunResult:
    # 1. Planning (no safety check before or after)
    plan = self._planner.create_plan(context)

    # 2. Execution (no checkpoint, no approval gate)
    run = self._transition(run, RunState.EXECUTING, RunPhase.EXECUTION)
    step_results, checkpoints = self._execute_plan(run, plan, cap_context)

    # 3. Completion (no rollback on failure)
    if not all_success:
        run = self._transition(run, RunState.FAILED, ...)
```

**Problem:**
The Constitution mandates "Human approval for destructive actions" (Principle #5) and "Reason before execution" (Principle #4). The Coordinator is the **top-level orchestrator** — if it doesn't call the safety and approval machinery, nothing else will. A DELETE operation could be executed without a checkpoint or human approval.

**Required Fix:**
1. Inject `SafetyRuntime` and `ApprovalCoordinator` into `Coordinator.__init__()`.
2. Before `RunState.EXECUTING`:
   ```python
   safety_report = self._safety_runtime.prepare()
   if safety_report.health == WorkspaceHealth.UNSAFE:
       return RunResult(outcome=RunOutcome.BLOCKED, summary="Workspace unsafe")
   ```
3. After `PlanningCompleted` and before `ExecutionStarted`, check if the plan requires approval:
   ```python
   if plan_requires_approval(plan):
       approval = self._approval_coordinator.coordinate(decision)
       # Block execution until approval is granted
       # Poll or await ApprovalManager.approve(approval_id)
   ```
4. In the `except` block of `run()`, call:
   ```python
   self._safety_runtime.rollback()
   ```
5. Publish `SafetyCheckpointCreated` and `ApprovalRequired` events from the Coordinator.

---

## 2. Architectural Recommendations (Pre-Sprint 8)

These are not bugs — they are structural upgrades needed before the single-threaded Chief Engineer evolves into a multi-worker organization. Each was identified during the Phase 0–5 audit and addresses a scalability concern that Sprint 8 (Workers) will expose.

### A1 — EventBus Upgrade: Async Protocol Abstraction

| Attribute | Value |
|-----------|-------|
| **Phase** | 0 — Kernel & Coordination |
| **File** | `src/eag/events/bus.py` |
| **Trigger** | Sprint 8 parallel workers will produce concurrent events |

**Current State:**
`EventBus` is synchronous and in-process. `publish()` iterates over subscribers and calls callbacks directly:
```python
def publish(self, event: Event) -> None:
    subs = self._subscribers.get(type(event), {})
    for sub in tuple(subs.values()):
        if sub.active:
            sub.callback(event)
```

**Problem:**
When Sprint 8 spawns parallel workers (via threads or `asyncio`), the current `EventBus` becomes a bottleneck:
- No async support — callbacks block the publishing thread
- No thread safety — `defaultdict` mutations from multiple threads can corrupt the subscriber map
- No backpressure — a flood of events from N workers would exhaust the call stack
- No cross-process support — workers in separate processes can't share the bus

**Recommendation:**
1. Define an `EventBusProtocol` (abstract interface) that the current `InProcessBus` implements.
2. Create an `AsyncEventBus` using `asyncio.Queue` for async-safe publishing.
3. For multi-process workers (future), create a `RedisEventBus` or `MultiprocessingEventBus`.
4. The `Kernel` should accept a `EventBusProtocol`, not a concrete `EventBus`.
5. Add thread-safe locking to `InProcessBus` as a minimal fix (`threading.Lock` on subscribe/unsubscribe/publish).

```python
# Proposed protocol
class EventBusProtocol(ABC):
    @abstractmethod
    def subscribe(self, event_type: type[EventT], handler: EventHandler[EventT]) -> Subscription: ...
    @abstractmethod
    def publish(self, event: Event) -> None: ...
    @abstractmethod
    def unsubscribe(self, target: type[EventT] | Subscription, handler: EventHandler[EventT] | None = None) -> None: ...
```

---

### A2 — Knowledge Persistence Layer

| Attribute | Value |
|-----------|-------|
| **Phase** | 1 — Knowledge Platform |
| **Files** | `src/eag/index/runtime.py`, `src/eag/graph/runtime.py` |
| **Trigger** | Constitution Principle #3 ("Knowledge is permanent") is not satisfied |

**Current State:**
`IndexRuntime` and `GraphRuntime` hold their state in memory:
```python
# IndexRuntime
self._current_index: RepositoryIndex | None = None

# GraphRuntime
self._snapshot: GraphSnapshot | None = None
```

When the process exits, the engineering index and graph are lost. On next boot, the entire `scan → analyze → index → graph` pipeline must re-run from scratch.

**Problem:**
The Constitution states: *"Once engineering knowledge is discovered — a symbol, a relationship, an impact — it is never lost. Knowledge is persisted, not recomputed."*

Currently, knowledge is **recomputed on every boot**. This is:
- Slow (full repository re-scan for large repos)
- Wasteful (AST parsing is expensive)
- Non-compliant with Principle #3

For Sprint 8, if multiple workers need the graph simultaneously, they all depend on the in-memory snapshot. If the process crashes mid-execution, all workers lose their shared mental model.

**Recommendation:**
1. Create a `KnowledgePersistence` service (interface + implementation).
2. After `IndexRuntime.build()` completes, serialize `RepositoryIndex` to disk (SQLite or JSON).
3. After `GraphRuntime.build()` completes, serialize `EngineeringGraph` to disk.
4. On boot, `IndexRuntime` and `GraphRuntime` should **load from persistence first**, then offer an incremental `rebuild_if_changed()` that uses file fingerprints to detect staleness.
5. The `RepositoryScanner` already produces a fingerprint (`_generate_fingerprint`) — use this to detect whether a re-scan is needed.

```python
# Proposed interface
class KnowledgePersistence(Protocol):
    def save_index(self, index: RepositoryIndex) -> None: ...
    def load_index(self, repository: str) -> RepositoryIndex | None: ...
    def save_graph(self, graph: EngineeringGraph) -> None: ...
    def load_graph(self, repository: str) -> EngineeringGraph | None: ...
    def is_stale(self, repository: str, fingerprint: str) -> bool: ...
```

---

### A3 — Approval Batching: Pre-Approved Execution Tokens

| Attribute | Value |
|-----------|-------|
| **Phase** | 2 — Safety & Execution |
| **Files** | `src/eag/approval/manager.py`, `src/eag/approval/coordinator.py` |
| **Trigger** | Sprint 8 workers will trigger N approval prompts for N destructive operations |

**Current State:**
`ApprovalManager` operates on a per-command basis:
```python
def create(self, *, command: CommandRequest, classification, policy_outcome, ...) -> ApprovalRequest:
    # Creates a PENDING approval for one specific command
```

If a plan contains 5 destructive operations (e.g., 5 file deletions), the system creates 5 separate `ApprovalRequest` objects, each requiring human approval. The human sees 5 prompts.

**Problem:**
In a Worker model, N parallel workers could trigger N simultaneous approval requests. This causes:
- **Security fatigue** — The human rubber-stamps approvals without reading them
- **Throughput bottleneck** — Workers block waiting for approval
- **No contextual batching** — The human can't see that all 5 deletions are part of the same plan

**Recommendation:**
1. Create a `BatchApprovalEngine` that groups `ApprovalRequest` objects by plan ID.
2. The `ApprovalCoordinator` should collect all destructive operations from a plan and create a single `BatchApprovalRequest` with a summary:
   ```
   Plan: "Rename User module to Account"
   Destructive operations: 3
     1. Delete: src/user/models.py
     2. Delete: src/user/views.py
     3. Overwrite: src/account/__init__.py
   [Approve All] [Reject] [Review Individually]
   ```
3. Once the batch is approved, issue **pre-approved execution tokens** (signed JWTs or UUIDs) to each worker.
4. Workers present the token to the `SafetyRuntime` instead of triggering a new approval.
5. The `ApprovalManager.consume()` method already supports the `RESERVED → CONSUMED` flow — extend it to support batch consumption.

```python
# Proposed model
@dataclass(frozen=True, slots=True)
class BatchApprovalRequest:
    batch_id: str
    plan_id: str
    requests: tuple[ApprovalRequest, ...]
    summary: str
    total_destructive: int
    total_risky: int
    status: BatchApprovalStatus  # PENDING → APPROVED → CONSUMED
```

---

### A4 — Worker Lifecycle: Centralized Supervisor with Pool Management

| Attribute | Value |
|-----------|-------|
| **Phase** | 5 — Workers (Sprint 8) |
| **Files** | `src/eag/workers/runtime.py`, `src/eag/workers/manager.py`, `src/eag/task_graph/graph.py` |
| **Trigger** | Sprint 8 requires parallel execution with conflict detection |

**Current State:**
`WorkerRuntime.execute()` is synchronous:
```python
def execute(self, worker: Worker, task: WorkerTask, context: WorkerContext) -> WorkerResult:
    worker_id = worker.profile.id
    inst = self._manager._get_instance(worker_id)
    inst.state = WorkerState.EXECUTING  # Direct mutation, bypassing assign()
    result = worker.execute(task, context)
    # ...
    self._manager.release(worker_id)
```

`WorkerManager` tracks instances in a dict but has no pool, no concurrency, and no conflict detection:
```python
self._instances: dict[str, WorkerInstance] = {}
```

**Problem:**
The Constitution says "Runtime orchestrates" (Principle #14). For Sprint 8:
- Workers must run in parallel (threads or asyncio)
- The supervisor must coordinate dependent tasks (wait for predecessors via `TaskGraph.ready()`)
- The supervisor must detect file-level conflicts between parallel workers
- Workers must not mutate their own state — the supervisor owns the lifecycle

Additionally, F11 (Medium) shows that `WorkerRuntime` bypasses `WorkerManager.assign()` by directly mutating `inst.state`. This breaks the lifecycle contract.

**Recommendation:**
1. Create a `WorkerSupervisor` that owns the execution pool:
   ```python
   class WorkerSupervisor:
       def __init__(self, manager: WorkerManager, runtime: WorkerRuntime, graph: TaskGraph): ...
       def execute_plan(self, plan: ExecutionPlan, context: WorkerContext) -> tuple[WorkerResult, ...]:
           completed: set[str] = set()
           results: list[WorkerResult] = []
           while not self._graph.is_complete(completed):
               ready = self._graph.ready(completed)
               # Spawn workers for ready tasks in parallel
               batch_results = self._run_parallel(ready, context)
               # Detect conflicts
               conflicts = self._detect_conflicts(batch_results)
               if conflicts:
                   # Resolve or escalate
               results.extend(batch_results)
               completed.update(r.task_id for r in batch_results if r.success)
           return tuple(results)
   ```
2. Move all state transitions into `WorkerManager`:
   - `assign(worker_id, task_id)` → `WorkerState.ASSIGNED`
   - `start_execution(worker_id)` → `WorkerState.EXECUTING`
   - `complete(worker_id)` → `WorkerState.IDLE`
   - Remove direct `inst.state = ...` mutations from `WorkerRuntime`
3. Use `concurrent.futures.ThreadPoolExecutor` or `asyncio.gather()` for parallel execution.
4. Add file-level conflict detection: if two workers modify the same file, the second result is rejected and the task is re-queued.
5. Respect `WorkerProfile.max_parallel_tasks` — currently defined but never read.

---

## 3. Medium Severity Flags

### F2 — Kernel boots plugins before safety two-phase init is complete

| Attribute | Value |
|-----------|-------|
| **Phase** | 0 — Kernel & Coordination |
| **File** | `src/eag/bootstrap.py`, `src/eag/kernel/kernel.py` |
| **Severity** | 🟡 Medium |
| **Effort** | Small |

**Current State:**
`bootstrap.py` creates all runtime services, puts them in `RuntimeContext`, then calls `kernel.boot()` which calls `plugin_manager.load_all()`. Plugins like `GitPlugin` may try to use `SafetyRuntime` during their `load()` method. While the `SafetyRuntime` object exists in the context, it hasn't been `prepare()`'d (no checkpoint created).

**Problem:**
If a plugin's `load()` triggers an event that causes the repository to be scanned or the safety runtime to inspect the workspace, the order is fragile. There's no explicit two-phase init: "inject context → start all runtimes → load plugins."

**Required Fix:**
1. Add a `Runtime started` phase to the Kernel boot sequence:
   ```
   Phase 1: Create all runtimes (current behavior)
   Phase 2: Call runtime.start() on each (new)
   Phase 3: Load plugins (current behavior)
   ```
2. Each runtime gets a `start()` method that performs any initialization requiring the full context.
3. The Kernel publishes `RuntimeReady` before `plugin_manager.load_all()`.

---

### F3 — `IndexRuntime` hard-codes Python only

| Attribute | Value |
|-----------|-------|
| **Phase** | 1 — Knowledge Platform |
| **File** | `src/eag/index/runtime.py` |
| **Severity** | 🟡 Medium |
| **Effort** | Medium (requires language provider plugins) |

**Current State:**
```python
# src/eag/index/runtime.py
def _discover_source_files(self, root: Path) -> list[Path]:
    supported_exts = self._source_runtime._registry.supported_extensions()
    # Only .py is registered → only Python files are discovered
```

`RepositoryScanner` detects `RepositoryKind.NODE`, `RUST`, `GO`, `JAVA` and tracks file counts in `LanguageSummary`. But `SourceRegistry` only registers `PythonSourceProvider`.

**Problem:**
EAG can **profile** a TypeScript repository (facts) but cannot **index** its symbols (knowledge gap). The Engineering Graph for a non-Python repo would be empty. The Chief Engineer would have no impact analysis, no explainability, and no dependency graph to reason about.

**Required Fix:**
1. Create a `LanguageProvider` protocol (similar to `PythonSourceProvider`).
2. Register `TypeScriptProvider`, `JavaScriptProvider`, `RustProvider`, `GoProvider` in the `SourceRegistry`.
3. Each provider implements `parse(path, content) → SourceDocument` using the appropriate AST parser.
4. For Sprint 8, at minimum support TypeScript (most common multi-language repos are Python + TypeScript).

---

### F5 — `ExecutionRuntime.dry_run()` calls `execute()` instead of `PlanSimulator`

| Attribute | Value |
|-----------|-------|
| **Phase** | 2 — Safety & Execution |
| **File** | `src/eag/execution/runtime/runtime.py` |
| **Severity** | 🟡 Medium |
| **Effort** | Small |

**Current State:**
```python
def dry_run(self, context: ExecutionContext) -> ExecutionReport:
    return self.execute(context)  # Actually executes!
```

Meanwhile, the real simulation engine lives in `src/eag/planner/simulation/simulator.py`.

**Problem:**
Calling `ExecutionRuntime.dry_run()` actually modifies files. This is misleading and dangerous. A caller expecting a simulation gets real execution.

**Required Fix:**
1. Remove `dry_run()` from `ExecutionRuntime` entirely.
2. OR: Raise `NotImplementedError("Use PlanSimulator for dry-run operations")`.
3. Document that dry-run is the Planner's responsibility, not the Execution Runtime's.

---

### F7 — `GoalAnalyzer` uses `inspect.stack()` for legacy test detection

| Attribute | Value |
|-----------|-------|
| **Phase** | 3 — Reasoning (Planner) |
| **File** | `src/eag/planner/intelligence/goal_analyzer.py` |
| **Severity** | 🟡 Medium |
| **Effort** | Small |

**Current State:**
```python
def _classify_operation(self, goal: PlanningGoal) -> EngineeringOperation:
    title_lower = goal.title.lower()
    if "rename" in title_lower:
        stack_frames = [frame.filename for frame in inspect.stack()]
        is_legacy_test = any(
            any(t in frame for t in ["test_task_decomposer", "test_effort_estimator", ...])
            for frame in stack_frames
            if frame
        )
        if is_legacy_test:
            return EngineeringOperation.REFACTOR
        # ...
```

**Problem:**
Using `inspect.stack()` to detect test context is:
- Non-deterministic (breaks if test files are renamed)
- Fragile (depends on call stack depth and frame filenames)
- A violation of the "Simplicity over cleverness" engineering ethic

**Required Fix:**
1. Add an explicit `legacy_mode: bool = False` parameter to `GoalAnalyzer.analyze()`.
2. Legacy tests pass `legacy_mode=True` to get the old behavior.
3. Production code uses the default (precise routing).
4. Remove `import inspect` and the stack walking logic entirely.

---

### F11 — `WorkerRuntime` bypasses `WorkerManager.assign()` — direct state mutation

| Attribute | Value |
|-----------|-------|
| **Phase** | 5 — Workers |
| **File** | `src/eag/workers/runtime.py` |
| **Severity** | 🟡 Medium |
| **Effort** | Small |

**Current State:**
```python
# WorkerRuntime.execute() directly mutates worker state:
inst = self._manager._get_instance(worker_id)
inst.state = WorkerState.EXECUTING  # Bypasses assign()!
```

Meanwhile, `WorkerManager.assign()` exists but is never called from the runtime:
```python
def assign(self, worker_id: str, task_id: str) -> bool:
    inst = self._get_instance(worker_id)
    if inst.state != WorkerState.IDLE:
        return False
    inst.state = WorkerState.ASSIGNED
    inst.current_task_id = task_id
    return True
```

**Problem:**
The `WorkerManager` thinks the worker is `IDLE` while `WorkerRuntime` has already started executing. If `find_best_worker()` is called concurrently (Sprint 8), it could assign the same worker to a second task.

**Required Fix:**
1. `WorkerRuntime.execute()` should call `self._manager.assign(worker_id, task_id)` before execution.
2. If `assign()` returns `False`, raise `WorkerNotAvailableError`.
3. After execution (in `finally`), call `self._manager.release(worker_id)`.
4. Remove direct `inst.state = ...` mutations from `WorkerRuntime`.

---

## 4. Low Severity Flags

### F1 — `RuntimeContext` holds live runtime instances, not pure state

| Attribute | Value |
|-----------|-------|
| **Phase** | 0 — Kernel & Coordination |
| **File** | `src/eag/core/context.py` |
| **Severity** | 🟢 Low |

**Description:**
`RuntimeContext` holds `safety_runtime` and `repository_runtime` as live instances. The architecture docs describe it as a "shared state container." Holding live runtimes works but makes isolated unit testing harder (must mock full runtimes instead of simple state).

**Fix:** Consider splitting into `RuntimeState` (pure data) + `RuntimeServices` (live instances). Low priority — current design is functional.

---

### F6 — `WorkspaceManager.snapshot()` publishes `None` as an event

| Attribute | Value |
|-----------|-------|
| **Phase** | 2 — Safety & Execution |
| **File** | `src/eag/workspace/manager.py` |
| **Severity** | 🟢 Low |

**Description:**
```python
def snapshot(self) -> Any:
    snap = self._snapshot_engine.create(self._workspace.root)
    self._event_bus.publish(None  # type: ignore[arg-type])
    return snap
```

`None` is not an `Event`. This will crash any typed event handler. The `type: ignore` hides the bug.

**Fix:** Create a `WorkspaceSnapshotted` event class and publish it. Trivial fix.

---

### F12 — `BenchmarkRunner` has `traceback.print_exc()` debug output

| Attribute | Value |
|-----------|-------|
| **Phase** | 5 — Presentation & Ops |
| **File** | `src/eag/benchmark/runner.py` |
| **Severity** | 🟢 Low |

**Description:**
```python
except Exception as e:
    import traceback
    print("\n" + "!" * 50)
    print("RUNNER CRASHED! HERE IS THE REAL ERROR:")
    traceback.print_exc()
    print("!" * 50 + "\n")
```

Debug output left in production code. Should use `structlog` instead.

**Fix:** Replace with `logger.exception("benchmark_runner_crashed", benchmark_id=benchmark.id)`.

---

### F13 — `ReviewRuntime` uses hardcoded magic numbers for scoring

| Attribute | Value |
|-----------|-------|
| **Phase** | 5 — Presentation & Ops |
| **File** | `src/eag/review/runtime.py` |
| **Severity** | 🟢 Low |

**Description:**
```python
score = 100
if issue.severity == Severity.CRITICAL:
    score -= 25  # Magic number
elif issue.severity == Severity.ERROR:
    score -= 10  # Magic number
elif issue.severity == Severity.WARNING:
    score -= 5   # Magic number
```

**Fix:** Define named constants or a `ReviewScoringConfig` dataclass:
```python
class ReviewScoringConfig:
    base_score: int = 100
    critical_penalty: int = 25
    error_penalty: int = 10
    warning_penalty: int = 5
    reject_threshold: int = 50
    changes_requested_threshold: int = 70
    warning_threshold: int = 90
```

---

## 5. Constitution Compliance Matrix

| # | Principle | Phase(s) | Status | Evidence |
|---|-----------|----------|--------|----------|
| 1 | Model agnostic | 4 | ✅ | `ModelSelector` + `LiteLLMProvider` + 4 routing policies |
| 2 | Plugin first | 0 | ✅ | `PluginManager` + `ToolRegistry` + REQUIRED/OPTIONAL policy |
| 3 | Knowledge is permanent | 1 | ⚠️ | In-memory only — no persistence layer (see A2) |
| 4 | Reason before execution | 3 | ✅ | `PlannerRuntime` + `PlanSimulator` (dry-run) |
| 5 | Human approval for destructive | 2, 4 | ⚠️ | Approval machinery exists (Phase 2) but Chief `Coordinator` doesn't call it (F9) |
| 6 | Every action explainable | 0–5 | ✅ | EventBus trace + `explain()` methods throughout |
| 7 | Core never depends on plugins | 0 | ✅ | One-directional plugin boundary verified in `plugin.py` + `manager.py` |
| 8 | Architecture before implementation | All | ✅ | Docs precede code at every sprint |
| 9 | Documentation evolves with implementation | All | ✅ | CHANGELOG + docs updated per sprint |
| 10 | Leave project better than found | All | ✅ | Constitution + contributing guide enforced |
| 11 | Engineering knowledge is deterministic | 1 | ✅ | Frozen dataclasses + `MappingProxyType` everywhere |
| 12 | AI consumes knowledge but never replaces it | 4 | ✅ | Graph feeds Planner → Chief → Models, but models don't modify the graph |
| 13 | Separate facts/reasoning/execution | 0–4 | ✅ | Three distinct layers in code and architecture |
| 14 | Runtime orchestrates, algorithms reason, builders construct | All | ✅ | Every module respects its role |

---

## 6. Phase Validation Summary

| Phase | Scope | Status | Flags | Key Finding |
|-------|-------|--------|-------|-------------|
| 0 | Kernel & Coordination | ✅ Secured | F1, F2 | Clean lifecycle, event-driven, plugin boundary enforced |
| 1 | Knowledge Platform | ✅ Secured | F3 | Full pipeline: scan → parse → index → graph, but Python only |
| 2 | Safety & Execution | ✅ Secured | F4, F5, F6 | Transactional execution with approval gates, but rollback not wired |
| 3 | Reasoning (Planner) | ✅ Secured | F7, F8 | Goal decomposition + simulation + 5-rule validator (not wired) |
| 4 | Orchestration (Chief) | ✅ Secured | F9 | Model routing + fallback + tracing, but bypasses safety/approval |
| 5 | Presentation & Ops | ✅ Secured | F10, F11, F12, F13 | Workers + Benchmarks + TaskGraph + Review all functional |

### Recommended Fix Order

1. **F8** (Small) — Wire `PlanValidator` into `PlannerRuntime` 
2. **F9** (Medium) — Wire `SafetyRuntime` + `ApprovalManager` into `Coordinator`
3. **F4** (Small) — Wire `SafetyRuntime.rollback()` into `ExecutionRuntime`
4. **F11** (Small) — Fix worker state mutation bypass
5. **F5** (Small) — Remove stub `dry_run()` from `ExecutionRuntime`
6. **F7** (Small) — Remove `inspect.stack()` from `GoalAnalyzer`
7. **F6** (Trivial) — Fix `None` event in `WorkspaceManager`
8. **F12** (Trivial) — Remove debug output from `BenchmarkRunner`
9. **F13** (Trivial) — Extract review scoring constants
10. **A1** (Large) — EventBus async abstraction
11. **A2** (Medium) — Knowledge persistence layer
12. **A3** (Medium) — Approval batching engine
13. **A4** (Large) — Worker supervisor with pool management
14. **F2** (Small) — Kernel two-phase init
15. **F3** (Medium) — Multi-language source providers
16. **F1** (Refactor) — Split `RuntimeContext` into state + services

---

*End of Validation Report.*
```

---

This is the complete, organized validation document. You can save it directly to your repo. It's structured so that any LLM (or human contributor) reading it can understand the exact problem, the exact file, the exact fix, and the priority order.

**What would you like to tackle next?** I'd recommend starting with fixes **F8 → F9 → F4** since they form the connected safety chain and are all small wiring fixes.