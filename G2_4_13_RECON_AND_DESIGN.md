# G2.4.13 Reconnaissance and Design

**Mode:** Reconnaissance/design with uncommitted implementation record.
**Published baseline:** `v2.4.12-g2.4.12` at `37101700df5b860959951bf99f20aad1c0bb104c`.
**Authorized documentation artifact:** This document.

## Executive disposition

> **Recommendation — exactly one next milestone:** **G2.4.13: Pre-Session Readiness Binding.**
>
> G2.4.13 should integrate the existing G2.4.10 workspace-custody evidence and G2.4.11 runtime-composition evidence into the existing G2.4.6.2/G2.4.8 session-creation decision, before any durable replay claim or session issuance. It introduces no runtime execution path and no new authority owner. `ControlledRuntimeSessionGate` remains the sole session/permit authority; custody and composition remain non-executing evidence validators.

The G2.4.12 rehearsal proved that the existing controls can be composed deterministically in the intended order using a fake executor. The next safety step is to make the two preparation attestations mandatory at the one existing operational handoff: **session creation**. This prevents a future caller from taking the activation → approval → session route without presenting exact, durable, validated custody and composition evidence.

## FACT — published controlled path

### Authority and evidence map

| Published boundary | Owner and current responsibility | Existing protection |
|---|---|---|
| G2.4.1 | Governed execution state machine | Immutable context/history, legal transitions, budgets, terminality |
| G2.4.2 | Verification authority | Deterministic objective verification inside the governed runtime lifecycle |
| G2.4.3 | Reflection/replanning authority | Fresh iteration artifact and recovery/replanning validation |
| G2.4.4 | Governed runtime | The sole serial lifecycle orchestrator when supplied by a caller |
| G2.4.5 | Durable audit observer | Immutable terminal/interruption projection and read-only query |
| G2.4.6.1 | Activation admission | Explicit caller confirmation, policy/isolation/audit binding validation, no execution |
| G2.4.9 | Human approval evidence | Durable immutable exact approval receipt bound to activation/runtime identities |
| G2.4.6.2 / G2.4.8 | Session authority and durable replay ledger | One session/permit path, cross-context activation/session replay refusal |
| G2.4.7.1 | Controlled invocation | Consumes an approved permit and dispatches one supplied executor once |
| G2.4.10 | Workspace custody evidence | Durable immutable attestation of prospective root identities and empty workspace, no workspace operation |
| G2.4.11 | Runtime composition evidence | Durable immutable manifest/attestation of declared runtime composition, no runtime construction or execution |
| G2.4.12 | Deterministic chain rehearsal | Test-only proof that the public controls can be called in the intended order before one fake dispatch |

### Current operationally meaningful path

The published, non-CLI, library-only operational path is currently:

```text
explicit caller confirmation
  → activation admission
  → durable human approval evidence
  → durable session creation / single-use permit
  → controlled invocation
  → supplied G2.4.4 runtime, if a caller supplies one
  → observer-only terminal audit
```

G2.4.10 custody evidence and G2.4.11 composition evidence are published, durable, and deterministic, but they remain opt-in evidence boundaries. Neither is yet required by the production session-creation or invocation operation. G2.4.12 deliberately demonstrated the desired order in a test-only rehearsal rather than adding a production coordinator.

## FACT — readiness gaps after G2.4.12

| Area | Repository-supported condition | Remaining gap |
|---|---|---|
| Production runtime composition | Composition manifests attest declarative identities/digests | Session creation can proceed without validated composition evidence; no proof that a future supplied executor matches the declared manifest beyond caller discipline |
| Workspace lifecycle ownership | Custody attests root isolation and an empty prospective workspace | No provisioning, population, containment enforcement, cleanup, quarantine, retention, rollback, or recovery owner |
| Environment/provider readiness | One-attempt/no-fallback policy is bound during activation | No live provider boundary, environment fingerprint, credential broker, egress policy, cost metering, or explicit real-provider authorization |
| Credential/egress controls | No provider/credential operational surface was introduced | No secret isolation, endpoint allowlist, network broker, redaction policy, or outbound audit path |
| Human governance lifecycle | Approval is durable and exact activation/runtime-bound | No expiration/renewal policy for governed approval, operator identity authentication, revocation lifecycle, or consolidated operator view |
| Interruption/recovery | Runtime/audit preserve no-continuation/no-replay posture | No disposable workspace disposition, recovery custody, or unified all-controls interruption record |
| Audit completeness | Durable terminal/interruption records and query exist | No durable start/control-chain provenance projection linking activation/approval/custody/composition/session/invocation to the terminal record |
| Operator visibility | Individual durable records exist | No read-only combined status/provenance projection |
| Capability expansion | Existing capability boundaries are unaffected | No evidence that generic capability execution is safe for production-governed operation; no expansion is warranted |
| CLI/autonomous migration | No legacy path consumes governed control packages | No operator workflow, lifecycle/containment, provider, or status readiness justifies migration |
| Benchmark coverage | EBS-027 proves intended all-controls test order | Missing production session-gate enforcement and proof that invalid preparation evidence cannot consume an activation claim |

## INFERENCE — architectural interpretation

The next risk is not insufficient evidence generation. It is **evidence optionality at the last pre-dispatch handoff**. A library caller can currently obtain a valid activation, approval, and session even when no custody or composition attestation is presented. The later invocation boundary correctly consumes only an approved session, but it cannot know whether preparation evidence was validated because those attestations are not part of session identity or issuance requirements.

Integrating these preconditions at session creation is safer than adding a new orchestration layer. The session gate already owns the decision whether a valid activation becomes a one-time permit. Requiring existing evidence before that decision does not create a second execution authority; it narrows the existing permit authority. It also permits a crucial fail-closed ordering rule: **a missing, mismatched, corrupt, or unavailable custody/composition evidence source must reject before the durable replay ledger records activation/session consumption**.

The milestone must not claim that this yields production workspace safety or real provider readiness. It merely makes trusted preparation a mandatory prerequisite to the existing controlled handoff.

## Candidate milestone comparison

| Candidate | Purpose | Architectural value | Primary risk | Authority impact | Dependencies | Deterministic benchmark |
|---|---|---|---|---|---|---|
| **A. G2.4.13 Pre-Session Readiness Binding — RECOMMENDED** | Require exact custody and composition attestations when G2.4.6.2 creates a session | Converts test-rehearsed preparation evidence into a mandatory, fail-closed permit prerequisite | Incorrect ordering could burn activation/session replay claims on evidence failure | No new owner; existing session gate remains sole permit authority | G2.4.8 ledger, G2.4.9 approval, G2.4.10 custody, G2.4.11 composition | **EBS-028** proves evidence failure before durable session claim/permit issuance |
| B. Workspace lifecycle owner | Provision, prepare, quarantine, clean, retain, or rollback disposable workspaces | Addresses operational filesystem safety | Destructive workspace authority, cleanup/retention policy, recovery semantics | New operational authority required | Custody binding, environment containment, operator governance | Disposable lifecycle and interruption benchmark |
| C. Environment attestation | Record host/runtime/config/dependency provenance | Improves reproducibility and drift evidence | Host inspection/subprocess/file-read authority; false assurance without containment | New evidence source or host-read seam | Composition manifest and workspace policy | Fixture-only attestation benchmark before any host probing |
| D. Provider/credential boundary | Define credential retrieval, endpoint/model policy, egress, metering, redaction | Necessary before live provider operation | Secret/network authority and availability coupling | New high-risk provider authority | Environment policy, operator approval, audit expansion | Denial/redaction-only benchmark, no network |
| E. Operator status projection | Read-only consolidated control-chain visibility | Improves diagnosis and governance usability | Premature cross-record correlation semantics; does not close permit gap | Read-only query surface only | Stable control-chain identity associations | Read-only no-side-effect query benchmark |
| F. Capability expansion | Add or expose new execution capabilities | Functional breadth | Expands mutation/egress/process surface before preparation is mandatory | Capability authority expansion | Workspace lifecycle, provider, audit, authorization | Capability-specific containment benchmark |
| G. CLI/autonomous migration | Expose the controlled path operationally | Usability | Converts library-only boundaries into production operations before readiness is established | Operational integration authority | All unresolved areas above | End-user acceptance and security regression |

## RECOMMENDATION — G2.4.13 Pre-Session Readiness Binding

### Purpose

G2.4.13 should require a caller presenting an activation receipt and governed human approval to also present exact, durable, validated workspace-custody and runtime-composition evidence before `ControlledRuntimeSessionGate.create_session(...)` can create a controlled session. The integration point is intentionally before the gate claims the activation receipt in the G2.4.8 replay ledger.

### Why now

G2.4.12 is the necessary precondition: it established a deterministic test-only proof that custody and composition can be checked before approval/session/invocation sequencing without adding a coordinator. The narrowest durable enforcement is now session issuance, because that is the sole existing handoff capable of leading to G2.4.7.1 dispatch.

### Why not the alternatives

Workspace lifecycle would add destructive authority. Environment attestation would introduce a host observation seam before it has an enforcement consumer. Provider/credential work would introduce secrets and network risk without controlling prerequisites. Operator projection improves usability but cannot prevent an unprepared session. Capability and CLI/autonomous directions widen execution before preparation is mandatory. Each alternative has a higher risk-to-control ratio than a narrow pre-session check.

### Scope

The proposed scope is limited to the existing `governed_session` boundary and deterministic test support/tests/EBS-028. A new package, runtime, factory, coordinator, CLI command, capability path, provider adapter, workspace operation, audit writer, or invocation change is out of scope.

`ControlledRuntimeSessionGate` may receive injected existing `WorkspaceCustodyGate` and `RuntimeCompositionGate` dependencies. It must validate caller-supplied evidence using their existing public read/validate contracts. It must not create attestations, construct a runtime, create a workspace, invoke an executor, or write audit records.

### Proposed contracts

A frozen aggregate input is recommended to avoid proliferating loose parameters:

```text
ControlledSessionReadinessEvidence
  - custody_request: WorkspaceCustodyRequest
  - custody_attestation: WorkspaceCustodyAttestation
  - composition_manifest: RuntimeCompositionManifest
  - composition_attestation: RuntimeCompositionAttestation
```

This aggregate is **not an authority** and contains no executor, session, permit, mutable metadata, provider credential, workspace handle, or operational method. It establishes only identity inputs for the existing custody/composition validators.

The session refusal vocabulary may need additive typed values, such as:

```text
MISSING_WORKSPACE_CUSTODY_EVIDENCE
WORKSPACE_CUSTODY_BINDING_MISMATCH
WORKSPACE_CUSTODY_STORE_UNAVAILABLE
WORKSPACE_CUSTODY_STORE_CORRUPT
MISSING_RUNTIME_COMPOSITION_EVIDENCE
RUNTIME_COMPOSITION_BINDING_MISMATCH
RUNTIME_COMPOSITION_STORE_UNAVAILABLE
RUNTIME_COMPOSITION_STORE_CORRUPT
READINESS_EXECUTION_ID_MISMATCH
READINESS_RUN_ID_MISMATCH
READINESS_RUNTIME_ID_MISMATCH
READINESS_ISOLATION_MISMATCH
```

Exact names are an implementation decision, but refusals must remain typed, deterministic, fail closed, and distinguish missing/mismatch/corrupt/unavailable classes.

### Ownership boundaries

| Concern | Owner after G2.4.13 | Explicit non-owner behavior |
|---|---|---|
| Custody evidence validation | G2.4.10 `WorkspaceCustodyGate` | Does not create a workspace or session |
| Composition evidence validation | G2.4.11 `RuntimeCompositionGate` | Does not construct/invoke a runtime or session |
| Approval validation | G2.4.9 `GovernedApprovalGate` | Does not issue a session/permit |
| Replay claims and session issue | G2.4.6.2/G2.4.8 `ControlledRuntimeSessionGate` | Does not dispatch a runtime |
| Permit consumption/dispatch | G2.4.7.1 invoker | Unchanged; receives only an issued session |
| Runtime lifecycle | G2.4.4 runtime | Unchanged; not constructed by G2.4.13 |
| Audit writing | G2.4.5 observer | Unchanged; G2.4.13 does not invoke it |

### Required validation order

```text
1. Structural readiness aggregate validation.
2. Exact custody attestation validation and cross-check to activation isolation:
   execution ID, roots, and workspace/source/audit identities.
3. Exact composition attestation validation and cross-check to runtime request:
   execution ID, run ID, runtime ID, and invocation binding identity.
4. Existing activation/approval validation.
5. Only then claim activation/session state in the G2.4.8 durable replay ledger.
6. Only then issue the existing controlled session.
```

The important invariant is that any readiness failure happens before replay-ledger mutation. A corrected evidence submission may therefore create one valid session from the same activation receipt; an issued/consumed valid session still remains globally single-use.

### Forbidden responsibilities

G2.4.13 must not add or alter:

- `ControlledChainRuntime`, coordinator, factory, executor discovery, runtime construction, or runtime execution;
- G2.4.7.1 invocation sequencing or dispatch behavior;
- G2.4.4 lifecycle/state-machine/verification/reflection behavior;
- provider calls, credentials, egress, retries, fallbacks, or model selection;
- workspace create/copy/populate/mutate/cleanup/delete/rollback operations;
- audit observation/writing/query behavior;
- CLI, autonomous loop, Chief, Coordinator, generic capability, or legacy-path imports;
- approval owner semantics beyond existing read/validate use; or
- persistence reset/delete/replay APIs.

## Deterministic benchmark proposal — EBS-028 Pre-Session Readiness Binding

EBS-028 should be standalone and use only disposable test roots plus existing deterministic fakes. It must not call G2.4.4, a provider, a mutation workflow, an audit writer, or a real executor.

### Success case

1. Create exact durable custody and composition evidence.
2. Create exact activation and durable approval evidence.
3. Supply one readiness aggregate to the session gate.
4. Assert a controlled session is created.
5. Assert no runtime/executor/provider/mutation/audit observer/workspace operation occurs.
6. Assert the ledger has claimed the activation/session only after all evidence succeeds.

### Critical ordering cases

| Case | Expected refusal | Required proof |
|---|---|---|
| Missing custody evidence | Typed readiness refusal | No session; no replay-ledger activation/session claim; corrected evidence can subsequently create one session |
| Altered custody root, execution ID, or isolation relation | Typed custody/readiness mismatch | Same no-claim property |
| Custody store unavailable or corrupt | Typed fail-closed refusal | Same no-claim property |
| Missing composition evidence | Typed readiness refusal | Same no-claim property |
| Altered composition runtime ID, run ID, component/invocation binding | Typed composition/readiness mismatch | Same no-claim property |
| Composition store unavailable or corrupt | Typed fail-closed refusal | Same no-claim property |
| Valid readiness then replayed activation/session | Existing G2.4.8 refusal | No second session/permit |
| Valid session then invoker consumes permit | Existing G2.4.7.1 behavior unchanged | No G2.4.13 execution authority, single dispatch remains covered by EBS-022/EBS-027 |

Suggested benchmark markers:

```text
PRE_SESSION_READINESS_REQUIRED=PASS
READINESS_FAILURE_BEFORE_REPLAY_CLAIM=PASS
CUSTODY_COMPOSITION_BINDING=PASS
SESSION_AUTHORITY_PRESERVED=PASS
NO_EXECUTION_AUTHORITY=PASS
EBS_028=PASS
```

## Failure matrix

| Failure class | Session outcome | Replay-ledger outcome | Execution/provider/workspace outcome |
|---|---|---|---|
| Missing evidence | Refuse | No claim | Zero |
| Exact-binding mismatch | Refuse | No claim | Zero |
| Evidence store unavailable/corrupt | Refuse fail closed | No claim | Zero |
| Existing activation/approval rejection | Existing refusal | No claim | Zero |
| Valid readiness and valid session | Existing session created | One normal claim | Still zero until G2.4.7.1 independently consumes permit |
| Session replay/consumption | Existing refusal | Existing global replay protection | Zero additional dispatch |
| Supplied runtime failure after invocation | Existing G2.4.7.1 typed failure | Permit remains consumed | No retry/new session path |

## Acceptance criteria

G2.4.13 is complete only if all of the following are demonstrably true:

| Criterion | Required evidence |
|---|---|
| Existing session authority is preserved | `ControlledRuntimeSessionGate` is still sole issuer; no new permit/session object or issuer exists |
| Readiness is mandatory for session creation | Missing custody/composition aggregate refuses before ledger claim |
| Exact cross-binding is mandatory | Root/runtime/execution/run/isolation/invocation identity changes refuse deterministically |
| Fail closed | Unavailable/corrupt custody/composition storage refuses before ledger claim |
| Existing replay protection is preserved | Valid sessions remain globally single-use across gate/store recreation |
| Invocation/runtime authority is unchanged | G2.4.7.1/G2.4.4 production files remain unmodified; no executor call in EBS-028 |
| Legacy isolation is preserved | No CLI/autonomous/Chief/Coordinator/capability imports or edits |
| Scope is narrow | Only governed-session readiness integration, necessary public contracts, tests/support, and EBS-028 change |
| Quality gates pass | Standalone EBS-028, targeted G2.4.1–G2.4.13 regression, autonomous regression, permitted full deterministic suite, Ruff, scoped MyPy, whitespace, protected-path audit |

## Migration impact

G2.4.13 must remain library-only. It changes the explicit `create_session(...)` caller contract by requiring readiness evidence, so it will require deterministic fixture migration for existing direct session tests and the G2.4.7.1 invocation fixture. That migration is acceptable only when it supplies evidence generated by the existing G2.4.10/G2.4.11 public gates.

There is no CLI migration, autonomous migration, Chief/Coordinator change, provider enablement, workspace operation, or legacy compatibility bridge in the milestone. Callers unable to present readiness evidence must fail closed instead of receiving a session. Any future operator, CLI, or autonomous integration remains separately unauthorized.

## Final design disposition

The reconnaissance and design recommendation is complete. The implementation described below was subsequently authorized as a separate, uncommitted G2.4.13 work item; its scope remains confined to this document’s recommended pre-session readiness binding.

## Implementation record

The implemented seam introduces immutable `ControlledSessionReadinessEvidence` and a read-only `ControlledSessionReadinessGate`. The new gate delegates custody and composition validation to the already published G2.4.10 and G2.4.11 gates. It cannot attest evidence, issue a session or permit, consume a permit, construct or execute a runtime, write audit records, access credentials, call a provider, or modify a workspace.

`ControlledRuntimeSessionGate.create_session(...)` now requires readiness evidence and calls the readiness gate after its existing pure activation/isolation preflight but before approval validation, durable replay-ledger claims, and session issuance. A missing, altered, unavailable, or corrupt custody/composition evidence path therefore refuses without mutating the replay ledger. A corrected exact evidence submission can then create one session through the existing G2.4.6.2/G2.4.8 authority; normal G2.4.8 replay refusal remains unchanged after successful issuance.

EBS-028 directly demonstrates valid readiness, missing and altered custody/composition rejection, no replay claim on every readiness refusal, later valid session creation with corrected evidence, existing activation replay rejection, unchanged G2.4.7.1 pre-dispatch runtime-binding refusal, and zero executor/provider/mutation/audit/workspace side effects. The deterministic fixture migrations only provide pre-existing empty roots and published evidence required by the new session contract; they do not add workspace operations to any authority owner.

```text
G2.4.13_RECON=COMPLETE
G2.4.13_DESIGN=COMPLETE
G2.4.13_IMPLEMENTATION=COMPLETE

READINESS_BINDING=PASS
CUSTODY_REQUIREMENT=PASS
COMPOSITION_REQUIREMENT=PASS
SESSION_PRESERVATION=PASS
NO_NEW_AUTHORITY=PASS
EBS_028=PASS

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

Implementation remains uncommitted and awaits a separate acceptance review. This record does not authorize publication, runtime activation, CLI exposure, autonomous migration, or provider use.
