# G2.4.6.2 Reconnaissance and Design — Controlled Activation-to-Runtime Handoff

**Design date:** 22 August 2026
**Published baseline:** [`v2.4.6.1-g2.4.6.1`](https://github.com/MenaYassa/EAG/tree/v2.4.6.1-g2.4.6.1) at `f6a34515cd13e9cb2ffa5389340f6659cb053934`
**Scope:** Analysis and architecture only
**Author:** Manus AI

> **Decision.** The next additive seam should be a **single-use controlled runtime session admission**. It must transform a valid G2.4.6.1 approval into an immutable, identity-bound session artifact that a dedicated start gate may consume exactly once to call the already-composed G2.4.4 runtime. The activation layer remains permission-only; it never calls `runtime.execute`.

## 1. Current Facts

**FACT.** G2.4.6.1 admits a prospective governed execution only through immutable caller confirmation, provider execution policy, three explicit isolation roots, and a required audit-observer capability. Its result is an immutable approval/refusal decision plus a policy digest. It has no runtime handle, no execution method, and no provider, mutation, verification, reflection, replanning, resume, retry, or replay method.[1]

**FACT.** G2.4.4 accepts one immutable `GovernedExecutionRequest` containing the execution/run identity, subject workspace/repository root, goal, bounded budget, allowed capabilities, mutation-intent policy, and one-attempt/no-fallback/no-schema-repair gateway policy. The runtime then creates the G2.4.1 context and owns the serial two-iteration lifecycle.[2] [3]

**FACT.** G2.4.5 is an optional runtime observer. The G2.4.4 runtime calls its preflight before beginning execution and records only terminal results; audit observation remains unable to advance state, authorize, mutate, verify, reflect, replan, resume, retry, or replay.[3] [4]

**FACT.** The present activation receipt does not carry a run ID, a runtime-request digest, an audit-binding identity, an issuance/expiry boundary, or an atomic consumption state. Therefore an approval alone cannot safely prove that the later runtime request is the request the caller originally admitted, nor can it prevent replay.[1]

## 2. G2.4.6.1 Inventory

| Published artifact | Current contribution | Missing handoff information |
|---|---|---|
| `CallerActivationConfirmation` | Explicit caller intent bound to one `execution_id`. | Single-use session identity, consumption state, expiry. |
| `ProviderExecutionPolicy` | One attempt, no fallback, no schema repair, positive bounded time/token/cost values. | Binding to the actual G2.4.4 `GatewayPolicy` embedded in the runtime request. |
| `ExecutionIsolation` | Explicit source, subject workspace, and audit roots; unsafe equality/subtree layouts rejected. | A session-level fingerprint proving the runtime request retained the admitted paths. |
| `GovernedActivationReceipt` | Approved/rejected disposition, execution ID, activation ID, policy digest. | Request digest, run ID, audit binding, issuance/expiry, replay prevention. |
| G2.4.4 request | Bounded execution payload. | Proof of admission and a single-use start permit. |
| G2.4.5 observer | Preflight and terminal observation. | A binding identity visible to session admission without observing or persisting a run. |

## 3. Missing Composition Seam

The missing boundary is not another lifecycle runtime and not a general composition factory. It is a narrow, deterministic **runtime start gate** between an approved admission result and exactly one call to an already-composed `GovernedEngineeringExecutionRuntime`.

```text
G2.4.6.1 admit(activation request)
    -> APPROVED_TO_START receipt
    -> deterministic bind(request + approved receipt + audit observer)
    -> immutable ControlledGovernedRuntimeSession
    -> one-time session start gate
    -> existing G2.4.4 runtime.execute(existing GovernedExecutionRequest)
    -> existing G2.4.1 / G2.3.x / G2.4.2 / G2.4.3 / G2.4.5 behavior
```

**INFERENCE.** Creating a runtime object inside activation would give admission an implicit execution role. Conversely, allowing callers to pass an approval receipt alongside an arbitrary request would permit identity, policy, path, or audit-observer substitution. The session must be created separately, be immutable, and bind each later runtime input before a start is permitted.

**RECOMMENDATION.** Add the future handoff package outside `eag.governed_activation`, `eag.governed_runtime`, and `eag.governed_execution`; for example, `eag.governed_session`. It should import public activation, runtime, and audit contracts only. Neither activation nor runtime should import the new session package.

## 4. Proposed Contracts

### 4.1 Immutable session artifact

```text
ControlledGovernedRuntimeSession
  session_id: opaque deterministic ID
  activation_id: approved activation receipt identity
  execution_id: exact activation/request identity
  run_id: exact G2.4.4 request identity
  request_digest: canonical digest of admitted runtime controls
  workspace_binding: resolved subject workspace identity/digest
  source_repository_binding: resolved source identity/digest
  audit_binding_id: opaque identifier for the required observer binding
  provider_policy_digest: exact approved provider-policy digest
  issued_at: trusted monotonic/session time
  expires_at: optional bounded expiry
  session_version: versioned contract
```

**RECOMMENDATION.** The session must contain only redacted/digested identifiers for its observable receipt. It may retain in-memory trusted `GovernedExecutionRequest` and observer references in a private wrapper for one library call, but it must never place credentials, raw provider output, authorization tokens, proposal content, or unrestricted workspace content in the public session artifact.

### 4.2 Binding rules

| Binding | Required check before start | Refusal on mismatch |
|---|---|---|
| Activation disposition | Receipt is `APPROVED_TO_START` and has no rejection reason. | `ACTIVATION_NOT_APPROVED` |
| Execution identity | Receipt, activation confirmation, isolation, session, and runtime request use the identical non-empty `execution_id`. | `EXECUTION_ID_MISMATCH` |
| Run identity | Session binds exactly one non-empty runtime `run_id`. | `RUN_ID_MISMATCH` |
| Provider policy | Runtime `GatewayPolicy` must be semantically equivalent to the approved one-attempt/no-fallback/no-schema-repair policy and declared limits. | `PROVIDER_POLICY_MISMATCH` |
| Isolation | Runtime workspace/repository root equals the admitted subject workspace; source/audit bindings remain distinct and unchanged. | `ISOLATION_BINDING_MISMATCH` |
| Audit | Exact observer binding is present and the session start gate holds it; runtime receives the same observer. | `AUDIT_BINDING_MISMATCH` |
| Freshness | Session is unused and, if expiry is enabled, not expired. | `SESSION_CONSUMED` or `SESSION_EXPIRED` |
| Runtime configuration | Runtime is a valid already-composed G2.4.4 public runtime and request passes its own existing contract. | `RUNTIME_CONFIGURATION_INVALID` |

### 4.3 One-time start protocol

**RECOMMENDATION.** The session store should expose a single atomic `consume(session_id, expected_digest)` operation. Consumption must occur immediately before the one allowed runtime call. The operation should produce a local `STARTED` record for diagnostics, not a new G2.4.1 state transition or audit history entry.

> **Boundary.** Consuming a session grants only permission to invoke an existing runtime with the already-bound request. It does **not** grant mutation authorization, transition the G2.4.1 state machine, preflight/record audit evidence itself, or classify runtime results.

## 5. Authority Model

| Layer | Sole authority | Explicit non-authorities |
|---|---|---|
| G2.4.6.1 activation | Decide whether a prospective request is eligible for a session. | Runtime invocation, lifecycle, gateway, mutation, verification, recovery, audit persistence. |
| G2.4.6.2 session gate | Bind and single-use admit one approved session to one existing runtime call. | State transition, budget debit, provider request, mutation authorization, verification, reflection, audit write. |
| G2.4.4 runtime | Sequence existing public seams for at most two iterations. | Direct mutation, direct provider transport, objective assertion, recovery policy ownership. |
| G2.4.1 state machine | Lifecycle legality, immutable ledger, budgets, terminality. | Provider, mutation, verification, session issuance. |
| G2.4.2 verifier | Objective verification and completion evidence. | Admission, mutation, lifecycle sequencing. |
| G2.4.3 reflection/replanning | Typed verification-failure recovery and freshness validation. | Admission, authorization reuse, session replay. |
| G2.3.1/G2.3.2 | Proposal translation, policy, one-time authorization, mutation, receipt. | Activation/session authority, generic capability dispatch. |
| G2.4.5 audit | Observer-only redacted evidence. | Admission, start permission, lifecycle, resume, replay. |

## 6. Failure Matrix

| Situation | Deterministic handoff behavior | Runtime/provider/mutation effect |
|---|---|---|
| Activation is denied | Do not create a session; return typed refusal. | None. |
| Approved activation but runtime dependency unavailable | Refuse before session consumption where composition is missing; otherwise mark a start attempt as unavailable without calling the runtime. | No provider/mutation. |
| Missing or substituted audit observer | Refuse `AUDIT_BINDING_MISMATCH`. | No runtime start. |
| Stale/expired/consumed session | Refuse; never regenerate a permit silently. | No runtime start, no replay. |
| Changed workspace/repository/audit paths | Refuse `ISOLATION_BINDING_MISMATCH`. | No runtime start. |
| Runtime request policy differs from admission | Refuse `PROVIDER_POLICY_MISMATCH`. | No provider call. |
| Runtime request is internally invalid | Let the existing request contract reject before lifecycle start; the session gate reports no successful start. | No provider/mutation. |
| Runtime is interrupted after start | Preserve G2.4.5's interruption semantics: no resume/replay through session. A new execution requires fresh activation/session and new authority. | No automatic continuation. |
| Terminal audit persistence fails | Preserve G2.4.5's explicit exception after terminal context, with no session replay or second runtime call. | No retry. |

## 7. Security Review

### Replay and stale approval prevention

**FACT.** Current activation approval is bound to an execution ID but has no consumption control.[1]

**RECOMMENDATION.** Bind a receipt to a single-use session ID, canonical request digest, and optional expiry. Use compare-and-swap consumption. A consumed, expired, or mismatched session is terminally refused, not refreshed.

### Identity and isolation binding

**FACT.** G2.4.6.1 already rejects audit placement in or below either the subject workspace or source repository.[1]

**RECOMMENDATION.** The future start gate must recompute resolved root bindings immediately before runtime invocation. It should not trust a mutable `Path` string, assume a symlink remains stable, or permit source/workspace/audit substitutions between admission and start.

### Audit continuity

**FACT.** G2.4.4's optional observer preflights before lifecycle start and records terminal results; G2.4.5 treats audit failure explicitly rather than retrying operations.[3] [4]

**RECOMMENDATION.** Bind the exact observer instance or immutable observer descriptor used at session creation, pass it unchanged to the runtime, and leave preflight/terminal persistence solely to the observer/runtime seam. The session gate must not write a shadow audit trail.

## 8. EBS-021 Specification

### Deterministic fixture

Use a disposable subject workspace, a distinct disposable audit root, a scripted gateway, the real G2.3.1 mutation runtime, real G2.3.2 workflow, real G2.4.1 state machine, real G2.4.2 verifier, real G2.4.3 recovery components, real G2.4.4 runtime, and a real G2.4.5 observer. No real provider, shell, Git, network, or source-workspace mutation is permitted.

### Success path

```text
valid G2.4.6.1 activation
  -> immutable bound session
  -> one-time start gate admits the existing G2.4.4 runtime
  -> runtime preflights the attached G2.4.5 observer
  -> governed execution begins and reaches its deterministic terminal fixture outcome
  -> terminal audit record is queryable
```

Required assertions include exact activation/session/request execution-ID binding, matching provider-policy digest, matching resolved isolation bindings, identical observer identity, exactly one runtime invocation, and the existing audit terminal evidence.

### Negative paths

| Case | Required assertion |
|---|---|
| Denied activation | Session creation/start rejected; runtime invocation count is zero. |
| Invalid activation | Typed refusal; runtime invocation count is zero. |
| Missing/substituted audit observer | Refusal before runtime invocation. |
| Stale/expired activation session | Refusal before runtime invocation. |
| Consumed session reused | Refusal; exactly one lifetime runtime invocation. |
| Runtime request policy/path/identity mismatch | Refusal before runtime invocation. |
| Runtime unavailable | Refusal without provider/mutation/verification/reflection/replan work. |
| Interrupted post-start execution | No session reuse, resume, replay, or duplicate mutation. |

The benchmark must prove:

```text
NO_RUNTIME_START_WITHOUT_ACTIVATION=TRUE
NO_ACTIVATION_EXECUTION_AUTHORITY=TRUE
NO_SESSION_REPLAY=TRUE
NO_RUNTIME_START_AFTER_BINDING_MISMATCH=TRUE
REAL_PROVIDER_CALLS=0
SHELL_INVOCATIONS=0
GIT_MUTATIONS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
EAG_SOURCE_WORKSPACE_MUTATIONS=0
```

## 9. Migration Strategy

1. Add a separate public session package and keep activation/runtime packages free of reverse imports.
2. Leave `create_governed_engineering_execution_runtime` unchanged; the future session gate receives an already-composed instance rather than modifying the runtime factory.
3. Do not change `eag build`, the CLI, autonomous factory, `AutonomousLoopRuntime`, Chief, Coordinator, or generic capability runtime.
4. Add deterministic unit tests and EBS-021 first; then run G2.4.1–G2.4.6.1 and autonomous regressions.
5. Defer any CLI/API exposure, real-provider trial, human approval workflow, or session persistence beyond a local deterministic one-time store to separately approved milestones.

## 10. Non-Goals

G2.4.6.2 should not introduce a new execution runtime, duplicate G2.4.1 state, alter budgets, add provider execution policy behavior, call a provider, create a mutation authority, run a capability, add human pause/resume, resume interrupted work, replay a session, migrate the CLI/autonomous path, implement a database or remote session service, create an audit UI, change G2.4.5 persistence, or add live-provider benchmarks.

## 11. Definition of Done

| Category | Required evidence |
|---|---|
| Session integrity | Immutable session binds approved receipt, execution/run identity, request/policy/isolation/audit digests, and one-time state. |
| Authority preservation | Static tests prove activation is permission-only, session admits one existing runtime call only, and all published owners retain their authority. |
| Failure safety | Every approval, path, policy, audit, expiry, replay, and runtime-availability mismatch refuses before runtime start. |
| Runtime safety | The existing G2.4.4 request and observer receive exact bound values; no runtime, provider, or mutation retry is introduced. |
| Benchmark | Standalone EBS-021 proves success, denial, invalid activation, audit absence, stale/replayed session, and zero unapproved runtime starts. |
| Regression | G2.4.1–G2.4.6.1 and autonomous regressions remain green; full deterministic suite, Ruff, MyPy, and whitespace pass. |
| Publication discipline | No real-provider, CLI, or legacy-path activation is performed without separate explicit authorization. |

## References

[1]: https://github.com/MenaYassa/EAG/blob/v2.4.6.1-g2.4.6.1/src/eag/governed_activation/models.py "G2.4.6.1 activation contracts"
[2]: https://github.com/MenaYassa/EAG/blob/v2.4.6.1-g2.4.6.1/src/eag/governed_runtime/models.py "G2.4.4 runtime request and result contracts"
[3]: https://github.com/MenaYassa/EAG/blob/v2.4.6.1-g2.4.6.1/src/eag/governed_runtime/runtime.py "G2.4.4 runtime lifecycle and audit preflight"
[4]: https://github.com/MenaYassa/EAG/blob/v2.4.6.1-g2.4.6.1/src/eag/governed_audit/recorder.py "G2.4.5 observer-only audit boundary"
