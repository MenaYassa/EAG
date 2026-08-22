# G2.4.4 Implementation Report — Opt-In Serial Governed Execution

## Status

```text
G2.4.4_IMPLEMENTATION=COMPLETE
RUNTIME_IMPLEMENTED=YES
OBSERVER_SEAM=PASS
STATE_AUTHORITY=PASS
MUTATION_AUTHORITY=PASS
VERIFICATION_AUTHORITY=PASS
RECOVERY_AUTHORITY=PASS
FRESH_ITERATION=PASS
NO_HIDDEN_RETRY=PASS
NO_THIRD_ITERATION=PASS
EBS_018=PASS
LEGACY_PATH_PROTECTION=PASS
```

## Delivered Boundary

G2.4.4 adds an explicit, synchronous, serial composition in the new `eag.governed_runtime` package. The package is intentionally outside `eag.governed_execution`: the published G2.4.1 state/ledger package remains import-isolated from operational gateway, mutation-workflow, workspace, autonomous, and generic-capability dependencies.

The opt-in `GovernedEngineeringExecutionRuntime` owns only lifecycle sequencing. It holds the immutable `GovernedExecutionContext` returned by the existing G2.4.1 state machine and maintains no shadow state enum, budget counters, terminal flag, mutation mechanism, authorization mechanism, verifier, reflection engine, or planner. An explicit factory constructs the runtime only when a caller supplies every public dependency; no autonomous factory, CLI, Chief, Coordinator, or legacy runtime invokes it.

| Authority | Preserved owner | G2.4.4 behavior |
|---|---|---|
| State, ledger, budgets, terminality | G2.4.1 state machine | Requests only legal transitions and uses returned immutable context. |
| Decision-to-mutation composition | G2.3.2 workflow | Uses the existing workflow; adds only an optional precondition observer. |
| Validation, authorization, atomic mutation | G2.3.1 runtime | Workflow continues to call existing public validation, authorization, and mutation operations. |
| Trusted verification and objective completion | G2.4.2 verifier/policy | Builds one trusted specification, verifies one receipt, and assesses objective through existing contracts. |
| Reflection, provenance, replanning, complete iteration freshness | G2.4.3 contracts | Consumes adapter, memory evidence, planner, ReplanningPolicy, and existing complete-artifact validator unchanged. |

## Freshness Boundary

`FreshIterationAuthority` is a new immutable G2.4.4 pre-mutation contract. It contains execution ID, iteration, context artifact/fingerprint, decision request/decision/proposal/authorization IDs. Its pure validator requires the same execution, exactly next serial iteration, and fresh values for every executable authority identity. It intentionally excludes receipt and verification IDs.

The existing G2.4.3 `FreshIterationArtifacts` is unchanged. After iteration-two receipt and verification exist, the runtime creates the complete artifact set and calls the existing `ReplanningPolicy.validate_fresh_iteration`; no G2.4.3 logic is split, weakened, copied, or reinterpreted.

## Workflow Observer

The G2.3.2 workflow now accepts an optional `GovernedMutationLifecycleObserver`. With no observer it retains the prior gateway → translation → `GovernedMutationRuntime.execute` path. With the opt-in observer, stages are gated before deciding, proposing, authorizing, and mutating. The runtime validates fresh iteration-two authority immediately after G2.3.1 authorization and before requesting the G2.4.1 `MUTATING` transition; mutation cannot occur if that gate refuses.

## Deterministic Evidence

| Validation | Result |
|---|---|
| FreshIterationAuthority plus unchanged G2.4.3 freshness suite | 33 passed |
| Workflow observer/default workflow regression | 25 passed |
| G2.4.4 runtime and EBS-018 tests | 5 passed |
| Consolidated G2.4.1–G2.4.4, G2.3 workflow, EBS-016–EBS-018 tests | 108 passed |
| Autonomous and normal EBS coverage | 163 passed, 3 skipped |
| Full repository suite | 3590 passed, 4 skipped |
| Scoped Ruff | PASS |
| Scoped MyPy | PASS |
| Whitespace | PASS |
| G2.4.1 import-isolation check | PASS |

EBS-018 uses a disposable fixture workspace, scripted gateway, real G2.3.2 workflow, real G2.3.1 mutation runtime, real G2.4.1 state machine, real verifier, and real G2.4.3 recovery contracts. Its primary path proves one recovery and fresh iteration-two authority followed by completion. Its negative path proves iteration-two verification failure terminates with `VERIFICATION_FAILED` and starts no third iteration.

## Preserved and Deferred Boundaries

No changes were made to the autonomous factory, CLI build path, `AutonomousLoopRuntime`, Chief, Coordinator, generic `CapabilityRuntime`, G2.3.1 mutation policy/authorization semantics, G2.4.1 state semantics, G2.4.2 verification semantics, or G2.4.3 reflection/replanning/complete-artifact semantics. The runtime request enforces `max_attempts=1`, `allow_fallback=False`, and `max_schema_repair_attempts=0`; deterministic tests use no provider.

G2.4.5 is not started.

## Changed Files

| File | Change |
|---|---|
| `src/eag/governed_execution/authority.py` | Additive immutable pre-mutation FreshIterationAuthority contract. |
| `src/eag/governed_execution/__init__.py` | Export only the non-operational additive authority contract. |
| `src/eag/governed_runtime/__init__.py` | New explicit opt-in composition public package. |
| `src/eag/governed_runtime/models.py` | Runtime request/result/context-artifact and verification factory contracts. |
| `src/eag/governed_runtime/runtime.py` | Serial lifecycle orchestration over existing public seams. |
| `src/eag/governed_runtime/factory.py` | Explicit caller-owned composition factory. |
| `src/eag/chief/intelligence/gateway/mutation_workflow.py` | Optional lifecycle precondition observer with preserved default behavior. |
| `tests/test_governed_execution_authority.py` | Fresh authority acceptance/rejection tests. |
| `tests/test_governed_mutation_lifecycle_observer.py` | Observer refusal and no-mutation proof. |
| `tests/test_governed_execution_runtime.py` | Serial success and bounded-negative runtime tests. |
| `tests/test_ebs_018_governed_serial_execution.py` | Deterministic EBS-018 benchmark. |
| `docs/architecture/G2.4_GOVERNED_ENGINEERING_EXECUTION_LOOP.md` | G2.4.4 design and implementation facts, updated for package isolation. |

## Stop State

```text
REAL_PROVIDER_CALLS=0
EBS_014_RERUN=NO
EBS_015_RERUN=NO
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
COMMITS=0
PUSHES=0
TAGS_CREATED=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
G2.4.5=NOT_STARTED
```

The worktree is intentionally uncommitted for review.

## Repository-Wide Static Analysis Separation

The G2.4.4 scoped Ruff and MyPy gates pass. Separate repository-wide runs remain blocked by inherited out-of-scope debt: Ruff reports five `B017` findings in `tests/test_adaptive_planning.py`; MyPy reports four pre-existing annotations/type-argument findings in `src/eag/adaptive/models.py`, `src/eag/adaptive/analyzer.py`, `src/eag/adaptive/planner.py`, and `src/eag/workers/manager.py`. No inherited-debt file was modified for G2.4.4.
