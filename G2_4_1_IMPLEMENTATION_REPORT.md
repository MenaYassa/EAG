# G2.4.1 Implementation Report — Governed Engineering Execution State Machine

**Date:** 21 August 2026
**Baseline:** `v2.3.2-g2.3.2` at `84d745314f71d532c89700bc89340412a114f78d`
**Scope:** Deterministic G2.4.1 state/ledger foundation only

## Milestone Outcome

G2.4.1 adds an isolated `eag.governed_execution` package. It contains a typed state taxonomy, deeply immutable public execution context, validated append-only transition ledger, ledger-derived aggregate budgets, typed terminal reasons, legal-transition guards, and minimal state-controller lifecycle events. The package is a deterministic orchestration contract only; it does not execute an engineering operation.

> **Boundary statement.** The state machine represents future governed lifecycle evidence. It does not call a provider, mutate a workspace, authorize a proposal, invoke a capability, verify an objective, reflect, replan, access Git, execute shell, use the network, or access credentials.

| Area | G2.4.1 implementation |
|---|---|
| State model | Fourteen typed lifecycle states, including explicit terminal `COMPLETED`, `FAILED`, and `ABORTED` states. |
| Transition guards | Approved legal transition matrix; rejected transitions return the unchanged immutable context, or the strict API raises `IllegalTransitionError`. |
| Ledger | Public reconstruction rejects any non-`CREATED` context without a complete contiguous ledger from `CREATED`; each record must be a legal edge, preserve iteration semantics, and reach the supplied state. |
| Budget model | Deterministic iteration, mutation, and verification limits with counters that must exactly equal legal entries into `CONTEXT_ASSEMBLING`, `MUTATING`, and `VERIFYING`, plus typed budget-exhaustion terminal reasons. |
| Stop taxonomy | Typed safe terminal reasons, independent of LLM/provider wording. |
| Events | Started, transitioned, and stopped events emitted after accepted state evolution; observer delivery is best-effort, never determines state correctness, and can lose telemetry when an observer raises. |
| Benchmark | Deterministic EBS-016 represents a two-iteration future lifecycle with fake references only; it performs no filesystem mutation or future integration. |

## Established Contract

The implemented legal transition matrix is intentionally restrictive. A new execution begins at `CREATED`, consumes an iteration budget only when it enters `CONTEXT_ASSEMBLING`, and may then represent planning, decision, proposal, approval, authorization, mutation, verification, reflection, and replanning stages. Terminal states accept no outgoing transitions.

| State | Legal successors |
|---|---|
| `CREATED` | `CONTEXT_ASSEMBLING`, `ABORTED` |
| `CONTEXT_ASSEMBLING` | `PLANNING`, `FAILED` |
| `PLANNING` | `DECIDING`, `FAILED`, `ABORTED` |
| `DECIDING` | `PROPOSING`, `FAILED` |
| `PROPOSING` | `APPROVAL_PENDING`, `AUTHORIZING`, `FAILED` |
| `APPROVAL_PENDING` | `AUTHORIZING`, `ABORTED` |
| `AUTHORIZING` | `MUTATING`, `FAILED` |
| `MUTATING` | `VERIFYING`, `FAILED` |
| `VERIFYING` | `COMPLETED`, `REFLECTING`, `FAILED` |
| `REFLECTING` | `REPLANNING`, `FAILED` |
| `REPLANNING` | `CONTEXT_ASSEMBLING`, `FAILED` |
| `COMPLETED`, `FAILED`, `ABORTED` | none |

The actual context stores references rather than duplicate full future artifacts. Its metadata and evidence metadata recursively freeze nested mappings, sequences, sets, and byte arrays, so post-construction aliases cannot alter stored ledger state. It can therefore represent plan, decision, proposal, authorization, receipt, verification, and reflection evidence while leaving G2.3.1/G2.3.2 contracts as the authorities for their own artifacts.

## Deterministic Evidence

The strengthened focused G2.4.1 suite contains deterministic proofs for initial state; complete legal lifecycle representation; invalid and strict illegal transition handling; terminal-state enforcement; typed terminal reasons; monotonic and exhausted budgets; rejected non-`CREATED` empty histories; rejected illegal, disconnected, terminal-extended, and state-mismatched ledgers; rejected fabricated mutation, verification, and iteration counters; accepted valid reconstruction; recursively immutable alias-safe metadata/evidence; deterministic event order; event-observer failure independence; forbidden operational dependency absence; and EBS-016’s two-iteration fake-reference contract.

| Validation | Result |
|---|---|
| Combined G2.4.1, G2.3.2, G2.3.1, gateway, context, and deterministic EBS tests | `109 passed, 1 skipped` |
| Autonomous regression | `3 passed` |
| Normal EBS regression | `8 passed, 3 skipped` |
| Full pytest suite | `3526 passed, 4 skipped` |
| Ruff | PASS |
| MyPy on `src/eag/governed_execution` | PASS |
| Whitespace | PASS |
| G2.4.1 forbidden dependency scan | PASS |

The skipped EBS lanes were explicit opt-in live-provider tests only. No `EAG_EBS013_LIVE`, `EAG_EBS014_LIVE`, or `EAG_EBS015_LIVE` execution was enabled.

## Deliberately Unchanged Existing Contracts

The following existing models and paths were inspected and intentionally left unchanged because they are either legacy autonomous/generic-execution contracts or per-mutation governed contracts rather than a compatible cross-iteration ledger:

| Existing contract | Reason it remains unchanged |
|---|---|
| `LoopState`, `LoopContext`, `LoopIteration`, and `AutonomousLoopRuntime` | Legacy generic autonomous execution remains a separate public path. |
| `RunState`, `RunPhase`, `RunContext`, `ChiefRun`, `RunResult`, and `Coordinator` | They describe one legacy Chief/capability run, not a future governed multi-step ledger. |
| `ChangeProposal`, `MutationAuthorization`, `MutationReceipt`, `GovernedMutationRuntime` | G2.3.1 remains the authoritative proposal/policy/authorization/mutation boundary. |
| `GovernedDecisionMutationWorkflow` | G2.3.2 remains the narrow one-shot gateway-to-mutation composition. |
| `CapabilityRuntime` and autonomous factory | The high-risk generic capability path remains unmodified and disconnected from G2.4.1. |
| Reflection, memory, verification, approval, provider, and benchmark runtime modules | Their integrations are reserved for later G2.4 milestones. |

## Safety and Non-Goals

```text
LLM_DIRECT_FILESYSTEM_ACCESS=NO
LLM_DIRECT_SHELL_ACCESS=NO
LLM_DIRECT_GIT_ACCESS=NO
LLM_DIRECT_NETWORK_MUTATION=NO
LLM_DIRECT_CREDENTIAL_ACCESS=NO

MUTATION_POLICY=AUTHORITATIVE
AUTHORIZATION=ONE_TIME_AND_PROPOSAL_BOUND
MUTATION=ATOMIC_AND_BOUNDED
PRESERVATION_REQUIREMENTS=ENFORCED
VERIFICATION=DETERMINISTIC
```

No LLM invocation, workspace mutation, capability dispatch, authorization consumption, verification execution, reflection execution, replanning execution, shell invocation, Git action, network call, provider configuration change, credential access, automatic retry, or live benchmark is part of this milestone.

## Changed Files

```text
G2_4_1_IMPLEMENTATION_REPORT.md
/docs/architecture/G2.4_GOVERNED_ENGINEERING_EXECUTION_LOOP.md
/src/eag/governed_execution/__init__.py
/src/eag/governed_execution/enums.py
/src/eag/governed_execution/errors.py
/src/eag/governed_execution/events.py
/src/eag/governed_execution/models.py
/src/eag/governed_execution/state_machine.py
/tests/test_ebs_016_governed_execution_loop.py
/tests/test_governed_execution_state_machine.py
```

## Final Status

```text
G2.4.1_IMPLEMENTATION=COMPLETE

STATE_MACHINE=PASS
TRANSITION_GUARDS=PASS
EXECUTION_LEDGER=PASS
STOP_REASONS=PASS
BUDGETS=PASS
EVENTS=PASS
DETERMINISTIC_BENCHMARK=PASS

G2.3.2_REGRESSION=PASS
G2.3.1_REGRESSION=PASS
AUTONOMOUS_REGRESSION=PASS
EBS_REGRESSION=PASS
FULL_SUITE=3526 passed, 4 skipped
RUFF=PASS
MYPY=PASS

EBS_015_RERUN=NO
EBS_014_RERUN=NO
REAL_PROVIDER_CALLS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
SHELL_INVOCATIONS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```

G2.4 remains open. G2.4.2 first-class verification, G2.4.3 reflection/replanning integration, G2.4.4 bounded governed execution composition, and G2.4.5 end-to-end benchmark work are not started.


## Remediation Update — Public Ledger Contract (21 August 2026)

An independent review identified three blocking public-contract weaknesses in the original G2.4.1 foundation: direct construction could represent a non-`CREATED` lifecycle without a valid ledger; aggregate counters could be supplied independently of lifecycle history; and the shallow mapping freeze left nested mutable aliases. This remediation changes only the G2.4.1 public models, their shared state-machine validation source, related deterministic tests, and affected G2.4 documentation.

> **Remediated guarantee.** A directly constructed `GovernedExecutionContext` is accepted only when it is the empty `CREATED` initial context, or when its complete immutable history starts at `CREATED`, uses contiguous sequence numbers and legal edges, preserves lifecycle iteration semantics, stops at the supplied state, has terminal reasons consistent with its last terminal record, and derives every consumed budget counter and aggregate evidence reference from that ledger.

| Review finding | Remediation |
|---|---|
| Impossible public lifecycle reconstruction | The public context rejects empty-history non-`CREATED` instances, disconnected/illegal histories, state mismatch, invalid terminal continuation, and invalid terminal-reason linkage. |
| Independently fabricated counters | `iterations_used`, `mutations_used`, and `verifications_used` must exactly equal legal entries into `CONTEXT_ASSEMBLING`, `MUTATING`, and `VERIFYING`. |
| Shallow immutable aliases | Context and evidence metadata now recursively freeze mappings, sequences, sets, and byte arrays; unsupported mutable/non-deterministic metadata is rejected. |
| Event observer failure ambiguity | Documentation now states that publication is best-effort: state correctness is complete before observer delivery, while a raising observer can cause telemetry loss. |

The state-machine controller remains the normal authoritative mechanism for evolution. The strengthened public model does not introduce any new operational behavior; it independently validates a reconstruction against the same shared legal-transition and terminal-reason contract.

### Remediation Validation

| Validation | Result |
|---|---|
| Expanded G2.4.1 state-machine/remediation suite | `30 passed` |
| Deterministic G2.4, G2.3.2, G2.3.1, gateway, and repository-context suite | `132 passed` |
| Autonomous regression plus normal EBS coverage | `159 passed, 3 skipped` |
| Ruff on touched G2.4.1 package and test | PASS |
| MyPy on `src/eag/governed_execution` | PASS |
| Whitespace | PASS |

Repository-wide Ruff currently reports five unrelated `B017` findings in `tests/test_adaptive_planning.py`. Repository-wide `mypy src/eag` currently reports four unrelated existing errors in `src/eag/adaptive/models.py`, `src/eag/adaptive/analyzer.py`, `src/eag/adaptive/planner.py`, and `src/eag/workers/manager.py`. None is in the G2.4.1 scope, and this remediation intentionally does not alter them.

```text
G2.4.1_REMEDIATION=COMPLETE

PUBLIC_CONTEXT_INVARIANTS=PASS
LEDGER_INTEGRITY=PASS
BUDGET_CROSS_VALIDATION=PASS
DEEP_IMMUTABILITY=PASS
DOCUMENTATION_ALIGNMENT=PASS
EVENT_BOUNDARY=PASS

G2.3.2_REGRESSION=PASS
G2.3.1_REGRESSION=PASS
AUTONOMOUS_REGRESSION=PASS
EBS_REGRESSION=PASS

RUFF=PASS
MYPY=PASS
WHITESPACE=PASS
REPOSITORY_WIDE_RUFF=INHERITED_FAILURE_OUT_OF_SCOPE
REPOSITORY_WIDE_MYPY=INHERITED_FAILURE_OUT_OF_SCOPE

PROVIDER_CALLS=0
REAL_PROVIDER_CALLS=0
WORKSPACE_MUTATIONS=0
OUTSIDE_WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
SHELL_INVOCATIONS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0

G2.4.3=NOT_STARTED
COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```
