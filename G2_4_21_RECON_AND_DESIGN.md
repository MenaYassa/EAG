# G2.4.21 Reconnaissance and Design — Governed Local Construction Work-Order Evidence

**Status:** Reconnaissance and design only.
**Published baseline:** `2749185ac44e38e86e4d1971a654ba26252e93a2`
**Latest published engineering milestone:** `v2.4.20-g2.4.20` → `2749185ac44e38e86e4d1971a654ba26252e93a2`
**Authorized artifact:** This document only.

> **Conclusion:** EAG has effectful legacy file and execution primitives, a bounded governed mutation owner, and a controlled one-shot runtime-invocation bridge. It does **not** yet have a legitimate owner for disposable-project provisioning, bounded multi-file construction, controlled local commands, process lifecycle, toolchain policy, or iterative correction. G2.4.21 should **not** introduce execution authority. The smallest safe next boundary is instead an immutable, non-executing **Governed Local Construction Work-Order Evidence Boundary** that defines the exact policy/binding vocabulary a later workspace-construction authority would have to consume.

This recommendation does not authorize a Todo application, a workspace, filesystem mutation, command execution, process launch, dependency installation, network access, provider call, credential access, deployment, publication, or recovery operation.

## 1. Executive finding

The published Gen2 chain contains strong governance and evidence controls, but they do not create the operational authority needed to construct software. A controlled construction workflow must eventually cause two classes of local effects: **workspace effects** such as creating a disposable project root and files, and **process effects** such as running a specific build or test command. Neither effect class has a current Gen2 owner that can be extended by implication.

The repository does contain legacy effectful seams. `GovernedMutationRuntime` owns a tightly bounded proposal-to-policy-to-authorization atomic **single-file** mutation path. The legacy `WorkspaceManager`, `LocalFilesystem`, and `WorkspaceCapability` expose direct file operations. The legacy `ExecutionRuntime` dispatches arbitrary registered executors, but the concrete built-in executor inspected is a no-op `DummyExecutor`; the generic execution contracts include command-shaped models but no reviewed governed command runner. These components are evidence of available mechanics, not authority to use them through the published Gen2 chain.[1] [2] [3] [4]

The correct design discipline is therefore to separate **pre-execution construction intent evidence** from **future local workspace effects** and from **future process effects**. Skipping that separation would give one combined object authority over project creation, writes, commands, process recovery, and iterative decision making before their inputs, limits, receipts, and stop conditions are specified.

## 2. FACT — published authority map through G2.4.20

| Milestone or boundary | Published owner | What it owns | What it does not own |
|---|---|---|---|
| G2.4.1–G2.4.5 | Governed state machine, bounded serial lifecycle, and durable audit | Lifecycle state, budgets, terminality, sequencing of existing seams, and audit observation. | Workspace provision, arbitrary file changes, command spawn, toolchain policy, or deployment. |
| G2.4.6.1 / G2.4.9 | Activation and human approval | Admission validation and identity-bound caller approval. | Runtime invocation, construction execution, filesystem change, or process control. |
| G2.4.6.2 / G2.4.8 | Controlled session gate and durable replay ledger | One approved, identity-bound, durable single-use runtime-start session. | Runtime implementation, workspace mutation, command execution, or outcome recovery. |
| G2.4.7.1 | Controlled runtime invocation | Consumes a valid session and dispatches one supplied runtime binding once. | Authority to define what the supplied runtime may do. |
| G2.4.10 / G2.4.11 | Workspace custody and composition evidence | Readiness/custody and runtime-composition attestations used at session admission. | Project-root creation, file creation, process isolation, or command allowlisting. |
| G2.4.12 / G2.4.13 | Controlled-chain rehearsal and readiness ordering | Deterministic proof that existing owners sequence before one fake executor dispatch. | A production executor or software-construction capability. |
| G2.4.14 | Artifact readiness evidence | Read-only evidence that a supplied artifact snapshot satisfies readiness/hygiene rules. | Generating the artifact, running commands, package build, installation, or release. |
| G2.4.15 | Promotion eligibility evidence | Logical eligibility bound to readiness and lineage. | Endpoint selection, request formation, transition execution, or destination effect. |
| G2.4.16 | External transition authorization | Immutable human authorization for one external-artifact transition. | Local project construction, permit issuance, external attempt, or receipt. |
| G2.4.17 | Transition-control ledger | **Sole** durable, fail-closed pre-execution duplicate/conflict/ambiguity control for the one supported external-artifact-transition profile. | Local construction control, process ownership, completion, retry, rollback, or reconciliation. |
| G2.4.18 | Destination-contract evidence | Structural, immutable declared destination-contract evidence. | Trust root, issuer verification, endpoint/client, credential, request, receipt, or destination truth. |
| G2.4.19 | Outcome-semantics policy evidence | Safe future external outcome taxonomy and stop semantics bound to G2.4.18. | Attempt/outcome/receipt/completion evidence, retry, rollback, reconciliation, or effect. |
| G2.4.20 | Declared attestation-policy evidence | Static policy compliance of declared G2.4.18 issuer/reference metadata. | Issuer authentication, signature/source verification, contract trust, destination truth, or execution readiness. |

The currently published controlled route is therefore:

```text
caller intent and approval evidence
        ↓
activation admission
        ↓
workspace custody + runtime composition readiness evidence
        ↓
durable replay-protected single-use session
        ↓
controlled single dispatch to a supplied G2.4.4 runtime
        ↓
existing bounded mutation/verification workflow only

separate external-artifact evidence chain:
readiness → promotion eligibility → human transition authorization
        ↓
G2.4.17 control → G2.4.18 destination contract
        ↓
G2.4.19 outcome policy → G2.4.20 declared attestation policy
```

No arrow in either chain grants a general local construction executor.

## 3. FACT — current execution-capability inventory

The following table records repository-supported mechanisms. “Available” means source-level mechanics exist; it does not mean that using them is authorized through the Gen2 authority chain.

| Existing component | Mechanical capability | Current owner/status | Gen2 construction use today |
|---|---|---|---|
| `GovernedEngineeringExecutionRuntime` | Sequences at most two governed iterations through context assembly, gateway decision, mutation workflow, verification, reflection, and replanning. | G2.4.4 lifecycle composer; opt-in and supplied-seam dependent. | Not a general construction owner. It does not provision a project, create directories, run builds/tests, or own a command process. |
| `GovernedMutationRuntime` | Atomically creates or replaces one permitted file under an existing workspace root; verifies a fingerprint; conditionally restores on postcondition mismatch. | G2.3.1 bounded mutation owner. | Effectful, but insufficient for multi-file project creation and not bound to a construction work order, workspace lease, or command policy. |
| `ControlledRuntimeInvoker` | Consumes one durable session and calls `runtime_binding.executor.execute(runtime_request)` exactly once. | G2.4.7.1 invocation bridge. | A legitimate dispatch seam, not an executor owner. It must not acquire construction semantics by accepting an arbitrary runtime. |
| `ControlledRuntimeSessionGate` | Validates activation, approval, readiness, audit observer, composition, and durable replay state before issuing/consuming a runtime-start session. | G2.4.6.2/G2.4.8 session owner. | Preserves admission/replay controls only; it does not create a workspace or run a command. |
| `GovernedWorkspaceCustody` evidence | Attests a supplied workspace root and custody bindings. | G2.4.10 evidence owner. | Does not create, clean, lease, or destroy a project workspace. |
| Legacy `WorkspaceManager`, `LocalFilesystem`, and `WorkspaceCapability` | Direct read/write/create-directory/copy/move/delete operations. | Legacy workspace/capability layer. | Not governed by activation/session/invocation controls; must not be adopted implicitly. |
| Legacy `ExecutionRuntime`, `Dispatcher`, and `Executor` protocol | Generic scheduled dispatch to a registry-selected executor; command-shaped request/result models exist. | Legacy execution layer. | Generic and under-constrained. The reviewed concrete built-in executor is `DummyExecutor`, a no-op. No reviewed governed command-runner seam exists. |
| Git provider and safety backends | Repository operations and subprocess-based Git control. | Legacy VCS/safety components. | Not a substitute for controlled construction or command execution; no authorization is implied. |

### 3.1 Existing authority is real but insufficient

`GovernedMutationRuntime` is the closest existing local effect authority. It has important safeguards: proposal validation, authorization consumption, atomic writing, fingerprint verification, and a narrow conditional restore. Its contract, however, is deliberately about one existing target file and one known content proposal. It does not define project initialization, parent-directory creation, allowed file-set expansion, dependency materialization, build commands, process lifetime, output capture, or a multi-action construction receipt.[1]

Similarly, `ControlledRuntimeInvoker` is a valid one-shot handoff seam. It receives an already bound runtime executor and dispatches it only after session consumption. Its type check establishes that the supplied executor exposes `execute(request)`, but it does not analyze the executor’s operational authority. Consequently, binding a new broad construction runtime behind this interface without a distinct construction policy would bypass the very ownership question G2.4.21 must settle.[5]

## 4. Semantic gap between evidence and software construction

The current chains answer whether supplied evidence is structurally valid, admitted, replay-protected, safely classified, or logically eligible. A Todo-app workflow requires different questions:

> “Who is allowed to create this disposable workspace, which paths may be created or changed, which exact local commands may start, under what process/output/resource limits, how are results represented, and when must the workflow stop rather than automatically repair or recover?”

None of G2.4.14–G2.4.20 answers those questions. The G2.4.4 runtime can sequence a pre-existing bounded mutation workflow, but it does not define a construction action language. G2.4.17 is not an available substitute: its sole supported profile is `external_artifact_transition_control_v1` and its durable key binds G2.4.16 external-authorization, artifact, destination, promotion, and external transition identities. Applying it to local construction would either misrepresent a workspace effect as an external artifact transition or require a forbidden profile/semantic expansion.[6]

Therefore, **G2.4.17 must remain untouched and must not govern the first local construction transition under its current contract**. The existing session replay ledger can continue to protect one runtime start, but it cannot define idempotency, conflict, state, or recovery semantics for individual construction actions.

## 5. Todo-app capability mapping

The Todo-app request is a capability probe, not authorization to build an application.

| Workflow step | Current state | Existing relevant owner | Missing legitimate authority |
|---|---|---|---|
| User request | Partially available as caller/goal input. | Existing caller, Chief, and governed runtime request contracts. | Construction-specific intent normalization and bounded work-order semantics. |
| Requirements and architecture | Existing planning/context seams can represent inputs. | Chief/gateway/adaptive planning seams. | Trustworthy construction specification binding; no generated plan is an execution permit. |
| Project/workspace creation | Not supported by the published governed chain. | Legacy filesystem/workspace mechanics only. | Disposable workspace-provisioning authority with root/ownership/isolation/cleanup policy. |
| Source-file creation | Only bounded per-file mutation mechanics exist. | G2.3.1 mutation runtime; legacy direct writers. | Construction action policy controlling allowed paths, parent creation, file count, bytes, and ordered plan. |
| Dependencies | Not authorized. | No reviewed governed dependency authority. | Dependency source, lockfile, integrity, offline/cache, network, and credential policy. |
| Build and tests | Command-shaped legacy models exist; no reviewed governed command runner. | Legacy execution contracts only. | Exact command allowlist, executable identity, argv grammar, working directory, environment, timeout, output cap, process-tree lifecycle, and result evidence. |
| Inspect failures | Some deterministic mutation verification exists. | G2.4.2/G2.3.1 local fingerprint verification. | Bounded local process-result inspection semantics and an explicit distinction from external receipts. |
| Modify after failure | Bounded mutation exists but does not grant automatic correction. | G2.3.1 mutation path. | A new human/work-order-authorized construction iteration policy; not automatic retry/reconciliation. |
| Rebuild/retest | Not authorized. | No governed command authority. | A fresh, separately bounded command-action authorization. |
| Working application | Not established by current evidence. | G2.4.14 may later assess a supplied artifact snapshot. | Definition of local completion, artifact handoff, and any later readiness invocation; never automatic publication. |

A full Todo-app workflow is therefore **not currently executable through a legitimate authority chain**.

## 6. Candidate next boundaries

| Candidate | Owner and capability | Value | Primary risk | Relationship to existing chain | Decision |
|---|---|---|---|---|---|
| **A. Continue evidence-only milestones** | New immutable construction-work-order policy assessor; no effects. | Defines exact local-construction intent and constraints before an effect owner exists. | May be mistaken for execution readiness unless positive semantics remain narrow. | Can bind custody/composition/readiness identities without changing their owners. | **Recommended.** |
| B. Workspace/file construction authority | New owner for root creation and bounded file actions. | Would enable a first disposable project skeleton. | Requires unresolved workspace lease, path/symlink policy, action grammar, content limits, cleanup, and receipt semantics. | Could consume a future work order and delegate bounded writes to G2.3.1 where compatible. | Defer. |
| C. Controlled command/build authority | New owner for one exact local command process. | Would enable build/test observation. | Requires executable provenance, argv policy, environment isolation, timeout/resource limits, process-tree termination, output handling, and dependency/network policy. | Must be separate from workspace write ownership and from G2.4.17. | Defer. |
| D. Combined software-construction executor | One runtime owning provisioning, writes, commands, tests, and iteration. | High apparent convenience for a Todo app. | Combines multiple effect/trust domains and creates premature recovery/continuation authority. | Would overload G2.4.4 and G2.4.7.1 dispatch seams. | Reject as next step. |
| E. Defer execution without a new boundary | No new contract. | Lowest immediate effect risk. | Leaves the required construction vocabulary undefined. | Preserves all existing boundaries. | Less useful than A; A is equally non-executing and reduces future ambiguity. |

## 7. Recommended G2.4.21 boundary

### 7.1 Name and purpose

The smallest safe next boundary is **G2.4.21 — Governed Local Construction Work-Order Evidence Boundary**. It should be immutable, deterministic, library-only policy evidence. It would determine only whether one supplied local-construction work-order declaration is structurally complete, within a single supported static profile, and exactly bound to declared readiness/custody/composition/approval identities.

A positive future disposition should be named **`CONSTRUCTION_WORK_ORDER_ATTESTED`**. It must mean only that a static work order is valid evidence for later consumption by a separately authorized effect owner. It must not mean workspace created, files written, command permitted or launched, dependency resolved, test passed, application working, result inspected, correction authorized, or execution allowed.

### 7.2 Proposed immutable public contracts for a future implementation

| Contract | Canonically bound content | Explicit exclusions |
|---|---|---|
| `LocalConstructionWorkOrderEvidence` | Work-order ID/digest; construction profile; source requirements digest; architecture/specification digest; exact workspace-custody and composition evidence identities/digests; declared workspace identity; approved capability IDs; bounded action-plan digest; static limits for files/bytes/actions/commands; issuance/expiry. | Absolute paths, executable paths, shell text, environment values, network endpoints, credentials, dependency URLs, keys, file content, callbacks, executor handles, client handles, sessions, permits, receipts, stores, recovery commands. |
| `ConstructionWorkOrderAssessmentRequest` | One immutable work order and exact supplied upstream evidence declarations. | Runtime executor, workspace manager, filesystem, command runner, process handle, G2.4.17 ledger, G2.4.18–G2.4.20 re-assessment, audit writer, cache, registry, or observer. |
| `ConstructionWorkOrderFinding` | Typed structural/binding/expiry/profile finding and non-operational recommendation. | Effect result, command result, filesystem state, completion, retry, rollback, recovery, or publication outcome. |
| `ConstructionWorkOrderAssessment` | Assessment identity, work-order identity, disposition, immutable findings/references/recommendations, digest, and timestamp. | Permit, session, runtime-start decision, workspace lease, action receipt, process result, completion claim, or deployment/release state. |
| `ConstructionWorkOrderAssessor` | Pure static validation of supplied immutable evidence. | Workspace creation, write, command spawn, process management, provider/network access, credential handling, ledger operation, or audit write. |

The initial supported profile should be singular and conservative, for example `disposable_local_construction_work_order_v1`. Multiple work orders, policy selection, precedence, conflict resolution, registry ownership, and reconciliation must remain unsupported/deferred.

### 7.3 Validation and fail-closed model

A future work-order assessor should validate in this order:

1. Require exact immutable types, complete field set, schema, UTC timestamps, canonical digests, and no expired work order.
2. Bind one declared workspace-custody identity/digest and one runtime-composition identity/digest without recreating or reassessing G2.4.10/G2.4.11 evidence.
3. Bind the declared caller approval/activation identity only as supplied evidence; do not issue or consume a session or permit.
4. Require the sole supported static construction profile and exact bounded action-plan/capability declarations.
5. Produce immutable assessment evidence only.

| Condition | Required disposition | Effect rule |
|---|---|---|
| Exact supported, non-expired work order and exact required declarations | `CONSTRUCTION_WORK_ORDER_ATTESTED` | Evidence only; no root, file, process, command, dependency, or result exists. |
| Missing, malformed, mismatched, expired, or tampered declarations | `NOT_ATTESTED` | Fail closed; no synthesis, fallback, or implicit broadening. |
| Unsupported profile or competing work order | `UNSUPPORTED_CONSTRUCTION_PROFILE` or unsupported/deferred | No policy selection, precedence, registry, or reconciliation. |
| Request to create/write/execute/test/inspect/retry/rollback | No public API | Capability absent. |

## 8. Minimum capability set before any execution implementation could be authorized

A later effectful milestone must not be approved until distinct owners and contracts exist for every required class below.

| Capability class | Minimum future authority requirement | Why it cannot be implicit today |
|---|---|---|
| Disposable workspace provisioning | A sole workspace-construction authority with a custody-bound root, root-existence rule, symlink/path traversal policy, lease/ownership model, and explicit cleanup disposition. | G2.4.10 attests supplied custody but does not create or lease roots. |
| Bounded multi-file construction | An action grammar for relative paths and create/replace actions; file/byte/action limits; parent policy; content/provenance bindings; per-action receipts. | G2.3.1 is a narrow single-file mutation path, not a project-plan owner. |
| Controlled local command | A distinct command authority with exact executable identity, argv grammar, fixed working-directory binding, sanitized environment, timeout/output/resource caps, process-tree handling, and local result evidence. | Legacy `CommandRequest` is not a governed command executor or policy. |
| Result inspection | A local result-evidence classifier for bounded command output/exit/timeout information; it must not be represented as a G2.4.19 external receipt. | Existing verification is proposal-fingerprint oriented, not general build/test interpretation. |
| Iterative correction | A new human/work-order-authorized iteration model that requires fresh bounded action evidence after a failure. | Automatic retry, reconciliation, and open-ended repair are not authorized. |
| Completion/handoff | A local construction completion definition that can supply an artifact snapshot to G2.4.14 readiness assessment, without publication. | G2.4.14 observes a supplied artifact; it does not generate one. |

## 9. Relationship to G2.4.17 and G2.4.18–G2.4.20

G2.4.17 remains the **sole external-artifact pre-execution transition-control ledger**. Its published profile and identities are not a legitimate local-construction control abstraction. G2.4.21 must not import, instantiate, claim, read, consume, reset, release, or reinterpret its ledger. A later local action-control ledger, if ever needed, requires independent design; it cannot be created by changing the meaning of a G2.4.17 claim.

G2.4.18, G2.4.19, and G2.4.20 remain external-transition evidence boundaries. When a future local executor exists, they remain evidence about a later external artifact transition, destination contract, outcome safety, and declared attestation policy. They do not authorize local construction, and local construction does not make their positive dispositions evidence of an external action, trusted destination, issuer authenticity, receipt, outcome, completion, release, or deployment.

The only legitimate future handoff is evidentiary: a bounded local-construction completion may produce an artifact snapshot that can be independently assessed by G2.4.14. If later promotion is considered, G2.4.15–G2.4.20 remain separately required and do not become execution APIs.

## 10. G2.4.21 deterministic benchmark proposal — EBS-036

**EBS-036 — Deterministic Local Construction Work-Order Evidence Boundary** should be a standalone static benchmark. It must use public immutable fixture declarations only and must not construct a workspace, call a runtime, mutate a file, start a process, or touch a network.

| Direct proof scenario | Required assertion |
|---|---|
| Exact supported work order bound to exact custody/composition/approval declarations | `CONSTRUCTION_WORK_ORDER_ATTESTED`; immutable references contain the exact identities/digests. |
| One-field authoritative mutation | Target differs; every other authoritative field is directly preserved; real assessor returns exact typed refusal without progression. |
| Work-order self-identity change | Distinct valid declaration/digest; no selection, precedence, conflict, registry, or reconciliation semantics. |
| Schema/timestamp/supplied-digest tamper | Strict public parser/constructor refusal with no fallback. |
| Missing required upstream declaration | Strict request-construction refusal; no assessor result is fabricated. |
| Immutable public state | Frozen/slots objects, no `__dict__`, no mutable containers, mutation refusal, and supplied inputs preserved. |
| Capability absence | Public API/import/source/call-path audit proves absence of workspace, filesystem, command, process, executor, client, network, credential, session, permit, ledger, receipt, retry, rollback, reconciliation, and publication surfaces. |

## 11. B5/B6 truthful proof model

The proof class must match the boundary actually designed.

| Classification | Correct use for G2.4.21 work-order evidence |
|---|---|
| `DIRECT_STATE_PROOF` | Immutable work-order/request/assessment payloads, digests, timestamps, and test-owned state are compared before and after pure assessment. |
| `CAPABILITY_ABSENT` | Workspace creation, file mutation, command/process lifecycle, network, credential, session, permit, ledger, receipt, retry, rollback, reconciliation, publication, and deployment have no reachable API/import/call path. |
| `OBSERVED_ZERO_EFFECT` | **Not applicable.** The proposed boundary has no reachable effect boundary. Literal counters, fake zero-effect dictionaries, sentinels, hooks, callbacks, observers, instrumentation, and artificial execution seams are prohibited. |

A later effectful authority may use direct observation of a genuine workspace or process boundary, but it must not claim observed zero effects where it has no reachable capability.

## 12. Explicit forbidden capabilities and deferrals

G2.4.21 must not introduce any literal or semantic equivalent of:

```text
create_workspace, mkdir, write, mutate, delete, copy, move,
execute, spawn, shell, command, process, build, test, install,
connect, request, download, network, credential, secret, key,
publish, release, deploy, receipt, complete, retry, rollback,
reconcile, recover, claim, consume, reset, ledger, permit, session
```

The following are explicitly deferred to separately authorized future design:

- workspace root provisioning, cleanup/destruction, lease ownership, filesystem isolation, symlink policy, and durable local action control;
- multi-file action grammar, file-content policy, directory creation, action receipts, and workspace-state observation;
- build/test executable policy, command allowlist, process spawning, environment construction, dependency source/integrity, timeout/resource bounds, process-tree termination, and output retention;
- package-manager, compiler, test-runner, database, container, browser, provider, network, credential, secret, and external service access;
- automatic correction, retry, rollback, reconciliation, resume, recovery, compensating action, or autonomous continuation;
- local completion authority, external publication/release/deployment, destination requests, receipts, or verification;
- changes to CLI, autonomous paths, Chief, Coordinator, generic capability runtime, G2.4.1–G2.4.20 public ownership, or published milestone tags.

## 13. Risks and unresolved ownership questions

| Risk or unresolved question | Why it blocks execution authority today | Required later decision |
|---|---|---|
| Workspace custody versus workspace provision | A custody attestation for an existing root does not state who may create or erase a new root. | Define a disposable-root lease, ownership, cleanup, and isolation model. |
| Legacy direct file writers | Existing legacy mechanisms can write outside the controlled chain. | Decide whether a new owner delegates only to a restricted actuator or replaces it under explicit migration approval. |
| Multi-file atomicity and failure | Single-file atomic write does not define a project-level partial-construction state. | Define action-level receipts and conservative stop semantics before multi-file construction. |
| Command/process policy | Arbitrary executable, arguments, environment, and process tree are broad local authority. | Define fixed profiles, executable provenance, argv grammar, resources, outputs, and termination. |
| Dependency acquisition | A normal Todo app may require packages, which can imply network, lockfile, and supply-chain decisions. | Begin with no-dependency/offline fixtures or separately design dependency custody. |
| Construction authorization | Existing human authorization is scoped to external artifact transitions. | Define whether and how a human authorizes a bounded local construction work order. |
| Failure interpretation and iteration | Build/test failure is neither a G2.4.19 external unknown outcome nor authority for automatic repair. | Require fresh work-order/action authorization for each correction stage. |
| Audit and completion | Existing audit observes G2.4.4 terminal contexts, not construction action/process facts. | Design local action/process evidence and audit projection without confusing it with external receipts. |

## 14. Migration constraints

No existing protected path should import a future G2.4.21 work-order package: CLI, autonomous runtime, Chief, Coordinator, generic capability runtime, governed runtime, activation, approval, session, invocation, workspace custody, composition, governed execution lifecycle, governed audit, G2.4.14 readiness, G2.4.15 promotion, G2.4.16 authorization, G2.4.17 transition control, G2.4.18 destination contract, G2.4.19 outcome policy, and G2.4.20 attestation policy.

A future construction work-order boundary may be consumed only by an explicitly designed later effect owner. It must not be retrofitted into the legacy generic `ExecutionRuntime`, generic executor registry, `WorkspaceCapability`, or direct filesystem layer without separate migration and acceptance authorization.

## 15. Recommendation and acceptance criteria

**Recommendation:** Approve no execution implementation for G2.4.21. If implementation is later authorized, implement only the static **Governed Local Construction Work-Order Evidence Boundary** and EBS-036. The architecture is not ready for a controlled Todo-app construction workflow, real provider integration, dependency installation, build/test command execution, production workspace mutation, CLI exposure, or autonomous-path migration.

A future G2.4.21 implementation would be acceptable only if all of the following are directly proved:

| Criterion | Required evidence |
|---|---|
| Evidence-only authority | Immutable frozen/slots public contracts, strict schema, canonical SHA-256 self-validation, UTC normalization, and no operational handles. |
| Exact construction binding | Exact supplied work order and declared custody/composition/approval bindings; no upstream re-assessment or permit/session consumption. |
| Conservative semantics | Positive result means static work-order validity only, never workspace/project/file/command/result/completion existence or execution authorization. |
| Fail-closed behavior | Missing, malformed, expired, tampered, mismatched, unsupported, or competing declarations yield typed refusal with no fallback. |
| B5/B6 truthfulness | Direct immutable-state proof plus capability-absence audit; no fabricated observed-zero-effect apparatus. |
| Existing-owner preservation | G2.4.17 ledger untouched; G2.4.18–G2.4.20 evidence-only semantics unchanged; no protected-path imports or changes. |
| No execution capability | No workspace, filesystem, command, process, provider, network, credential, receipt, retry, rollback, reconciliation, publication, or deployment API exists. |

## References

[1]: `./src/eag/mutation/runtime.py` — bounded G2.3.1 proposal/authorization/single-file mutation path, atomic write, verification, and conditional restore.

[2]: `./src/eag/workspace/manager.py` and `./src/eag/workspace/filesystem.py` — legacy direct workspace/file lifecycle mechanics outside the published Gen2 activation/session/invocation chain.

[3]: `./src/eag/execution/runtime/runtime.py`, `dispatcher.py`, `executor.py`, `dummy_executor.py`, and `./src/eag/execution/models.py` — legacy generic executor/command-shaped contracts and no-op built-in executor.

[4]: `./src/eag/governed_runtime/runtime.py` and `./src/eag/governed_runtime/models.py` — G2.4.4 bounded serial lifecycle composition and its fixed mutation/verification budget.

[5]: `./src/eag/governed_invocation/invoker.py` and `./src/eag/governed_invocation/models.py` — one-shot controlled dispatch to a supplied runtime binding, not a definition of executor authority.

[6]: `./src/eag/governed_transition_control/models.py` — G2.4.17 external-artifact transition-control profile and identity binding.

[7]: `./G2_4_20_RECON_AND_DESIGN.md` — published authority map and evidence-only deferrals through G2.4.20.

## Completion markers

```text
G2.4.21_RECON=COMPLETE
G2.4.21_DESIGN=COMPLETE
IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
FIXTURE_CHANGES=0
BENCHMARK_CHANGES=0
GIT_MUTATIONS=0

REAL_PROVIDER_CALLS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
EXECUTOR_OPERATIONS=0
WORKSPACE_MUTATIONS=0
COMMAND_EXECUTIONS=0

G2.4.22=NOT_STARTED
STOPPED_AFTER_RECON_AND_DESIGN=YES
```
