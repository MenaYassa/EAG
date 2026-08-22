# G2.4.7 Reconnaissance and Design

**Status:** Analysis only.
**Baseline:** Published `v2.4.6.2-g2.4.6.2` (`c3c18ad`).
**Author:** Manus AI.
**Implementation decision:** **Not authorized by this document.**

## Executive disposition

> **Recommendation:** The safest next milestone is **G2.4.7.1 — Controlled Session Invocation Boundary**. It should add one library-only invoker that can call the existing G2.4.4 runtime **only after** the published G2.4.6.1 activation and G2.4.6.2 single-use session gates have admitted the exact request. It must not add CLI activation, real-provider execution, new capabilities, pause/resume, or legacy-path migration.

The published platform now has strong components for state ownership, audit observation, activation admission, and process-local session admission. The remaining architectural gap is not another policy model; it is the absence of a narrow, authoritative **invocation bridge** that consumes a valid session permit and dispatches exactly one already-composed governed runtime call. Until such a bridge exists, a caller can construct the explicit G2.4.4 runtime directly, while the activation/session boundaries remain intentionally disconnected from runtime execution.[1] [2] [3]

| Question | Disposition |
|---|---|
| Is a bounded governed runtime published? | **Yes; FACT.** It is explicit, synchronous, fixed to two serial iterations, and owns lifecycle sequencing through G2.4.1. |
| Is durable audit observation published? | **Yes; FACT.** It can persist redacted terminal or interruption observations but offers no continuation authority. |
| Is controlled admission published? | **Yes; FACT.** Activation validates confirmation, provider policy, isolation, and audit-observer availability without composing a runtime. |
| Is a session handoff published? | **Yes; FACT.** A process-wide, single-use session gate binds an approved activation to an exact future runtime-start permit, but does not call the runtime. |
| Does an end-to-end controlled invocation path exist? | **No; FACT.** The missing handoff from an allowed session permit to the existing runtime is the immediate gap. |
| Is a real provider ready to be introduced? | **No; RECOMMENDATION.** Deterministic entry control should be completed first. |

## Evidence and analytical conventions

A statement marked **FACT** is directly grounded in the published repository contracts. A statement marked **INFERENCE** describes a capability or risk implied by those contracts. A statement marked **RECOMMENDATION** proposes a future, deliberately unimplemented milestone direction.

The G2.4 architecture document predates the now-published G2.4.4–G2.4.6.2 releases; its original sequencing is therefore treated as historical design context, while the tagged source is treated as the current behavioral baseline.[4]

## Published baseline

### Governed execution, audit, activation, and session boundaries

**FACT — G2.4.4 runtime composition.** `GovernedEngineeringExecutionRuntime.execute()` is an opt-in, caller-composed synchronous path. It obtains an explicit request, serializes access by workspace, runs at most two iterations, delegates lifecycle state and budgets to G2.4.1, delegates mutation to the existing workflow, delegates verification and reflection/replanning to their existing owners, and returns only terminal results.[1]

**FACT — G2.4.5 audit durability.** The audit recorder validates and persists redacted observations of authoritative contexts. Its runtime observer preflights audit-root placement and records terminal results after the runtime has reached a terminal context. Interruption records are readable evidence only; the query boundary explicitly rejects continuation and contains no resume operation.[5] [6]

**FACT — G2.4.6.1 activation admission.** Activation is a pure, library-only admission check. It requires caller confirmation bound to an execution ID; exactly one provider attempt with no fallback or schema repair; distinct workspace, source, and audit roots; and an audit observer capability. It returns a receipt or typed refusal and does not compose or execute the governed runtime.[2]

**FACT — G2.4.6.2 session handoff.** The session gate stores activation identities, immutable session records, and consumed-session identities in a process-wide lock-protected domain. It binds the execution ID, run ID, activation receipt digest, full runtime-request digest, policy digest, isolation digest, audit-observer identity, and runtime ID. A session can issue one `RUNTIME_START_ALLOWED` decision, while a repeat activation or consumed session is refused; the package does not invoke the runtime or observer.[3]

**INFERENCE — current controlled-execution posture.** The architectural perimeter needed for a controlled invocation exists, but it is not yet joined to the runtime. The runtime remains directly constructible by explicit library callers, and the session gate deliberately cannot exercise it. This is safer than accidental activation, but leaves the newly defined start permit unenforced at the eventual call site.

### What is executable versus opt-in only

| Surface | Published status | Execution status | Remaining limitation |
|---|---|---|---|
| G2.4.4 governed runtime | Published | Explicit library callers can invoke it | Not entered through G2.4.6 controls by default |
| G2.4.5 audit recorder/query | Published | Observer can persist/read audit evidence | Cannot resume or repair an interrupted execution |
| G2.4.6.1 activation | Published | Pure admission only | Does not construct or invoke a runtime |
| G2.4.6.2 session gate | Published | Pure permit issue/consume only | Does not dispatch the permitted runtime start |
| CLI/autonomous composition | Published legacy surfaces | Existing behavior unchanged | No governed activation/session integration |
| Live provider benchmarks | Existing opt-in evidence lanes | Not authorized in this analysis | Prior live evidence does not establish production readiness |

## Explicit gap assessment

### 1. Controlled execution activation

**FACT.** There is not yet a published end-to-end control path from `GovernedActivationReceipt` to a call of `GovernedEngineeringExecutionRuntime.execute()`. The activation package stops at admission, and the session package stops at a non-executing start permit.[1] [2] [3]

**INFERENCE.** A caller wishing to use the governed runtime still has two unsafe-in-the-architectural-sense options: call the runtime directly, bypassing the new admission/session perimeter; or recreate an ad hoc bridge, duplicating binding checks. Neither requires a real provider to expose the design problem.

**RECOMMENDATION.** G2.4.7.1 should introduce one explicit, library-only controlled invoker. It should consume the existing session permit first, then call a supplied runtime executor exactly once with the exact bound request. The invoker must contain no lifecycle, mutation, verification, reflection, or replanning logic; it should sequence the published gate and runtime only.

### 2. Human governance

**FACT.** The general approval subsystem already supports approval, reservation, release, consumption, expiry, exact-command matching, and atomic transitions in its store contract. It is not connected to governed activation, session, or runtime execution, and its currently published store implementation is in-memory.[7]

**INFERENCE.** G2.4.6.1 caller confirmation is a deliberate opt-in control, not a durable operator workflow. The audit layer offers evidence after terminality or interruption, but it does not create an operator pause point or durable approval tied to each governed lifecycle stage.

**RECOMMENDATION.** Do **not** add pause/resume in G2.4.7.1. Durable human intervention would require a separately designed paused-context contract, persistence and integrity rules, re-authorization semantics, and an explicit decision about whether any nonterminal state can ever be resumed. That work is larger and riskier than a one-call controlled invoker. A future milestone can adapt the existing approval primitives only after binding approval identity to governed execution identity and immutable request/session digests.

### 3. Provider readiness

**FACT.** The activation policy admits only a declarative one-attempt/no-fallback/no-schema-repair provider policy. The runtime can execute an existing gateway workflow, but neither activation nor session configures credentials, selects a provider, permits egress, or calls a model.[1] [2]

**INFERENCE.** The policy boundary makes a future provider invocation easier to constrain, but it does not establish live-provider reliability, transcript safety, credential isolation, model version pinning, or supply-chain trust.

**RECOMMENDATION.** Do not introduce a real provider in G2.4.7.1. Before controlled live evaluation, define a separate provider-readiness package covering allowlisted endpoints/models, environment-only secret injection, redacted request/response audit metadata, fixed failure/timeout semantics, egress policy, and explicit one-call opt-in benchmarking. No provider result should gain mutation authority.

### 4. Workspace lifecycle

**FACT.** The governed runtime expects its request workspace and repository path to resolve to the same root, while activation separately requires the source repository root and audit root to be distinct from the prospective workspace. Benchmark infrastructure uses disposable temporary fixtures and cleanup rather than a published persistent workspace lifecycle.[1] [2] [8]

**INFERENCE.** This is sufficient for deterministic tests and protects the source repository at admission time, but it is not a lifecycle policy for long-running or persistent workspaces. There is no published lease, ownership token, cleanup record, retention period, cross-process session durability, or recovery procedure.

**RECOMMENDATION.** G2.4.7.1 should require a caller-supplied, already-existing disposable workspace and retain the existing strict path binding. It should not create, copy, delete, or clean up workspaces. Persistent workspace ownership and cleanup should be designed independently after controlled invocation has deterministic proof.

### 5. Capability expansion

**FACT.** The governed request remains capability-allowlisted and uses the existing governed-mutation intent policy. The G2.4.4 runtime is intentionally an orchestration layer, not a capability registrar.[1]

**INFERENCE.** Adding a capability before the invocation boundary is complete would enlarge the operational surface without resolving the present admission-to-execution gap.

**RECOMMENDATION.** Add no capabilities in G2.4.7.1. The existing deterministic governed-mutation capability is sufficient to prove the bridge. Any new capability should require its own policy, authorization, verification, preservation, audit, and EBS design.

### 6. Security and trust model

**FACT.** Published activation/session contracts bind redacted digests and identities, avoid provider credentials, and enforce source/workspace/audit separation. The audit envelope is redacted and observer-only.[2] [3] [5]

**INFERENCE.** The following controls are still absent from a production readiness model: secret source and rotation policy, provider credential scope, TLS/egress governance, dependency and model-supply-chain attestation, persistent session integrity, cross-process replay prevention, workspace content classification, and operator identity provenance.

**RECOMMENDATION.** Keep the session domain process-local in G2.4.7.1. Restart behavior should fail closed because the in-memory permit domain disappears; it must not be reconstituted from audit. Treat cross-process durable activation/session state as a later security milestone requiring tamper-evident storage and explicit expiry/revocation semantics.

## Candidate milestone comparison

| Candidate | Value | Principal risk | Decision |
|---|---|---|---|
| **G2.4.7.1 — Controlled Session Invocation Boundary** | Completes the present deterministic control path with minimal new authority | Incorrect sequencing could create a second runtime authority | **Recommend** |
| Durable human pause/resume | Enables richer operator control | Unsafe nonterminal persistence/continuation semantics | Defer |
| Provider-readiness and live lane | Addresses availability and realistic model behavior | Credentials, egress, redaction, non-determinism | Defer |
| Persistent workspace lifecycle | Supports long-lived work | Cleanup/recovery/data-retention complexity | Defer |
| New capabilities | Expands usefulness | Multiplies policy and verification surface | Defer |

## Recommended G2.4.7.1 design

### Objective and authority split

The proposed invoker should accept a `ControlledRuntimeSession`, its activation receipt/request bindings, exact `GovernedExecutionRequest`, required audit observer, declarative `RuntimeAvailability`, and a runtime executor protocol. It should call `ControlledRuntimeSessionGate.consume_for_runtime_start(...)` once. Only if that returns `RUNTIME_START_ALLOWED` may it call `executor.execute(request)` exactly once. The executor remains the published G2.4.4 runtime or a test double; the invoker must not inspect or alter lifecycle state, workspace contents, provider responses, mutation proposals, verification results, reflection, replanning, or audit records.

| Concern | Existing owner | Future G2.4.7.1 invoker responsibility | Explicitly forbidden |
|---|---|---|---|
| Admission policy | G2.4.6.1 activation | Supply exact inputs to session binding | Alter policy or re-admit implicitly |
| Single-use permission | G2.4.6.2 session domain | Consume permit before dispatch | Reset, retry, reissue, or continue |
| Runtime lifecycle | G2.4.1 / G2.4.4 | Invoke once after permit | Transition state or own budgets |
| Mutation | G2.3.1/G2.3.2 | None | Call mutation directly |
| Verification | G2.4.2 | None | Verify or reinterpret outcomes |
| Reflection/replanning | G2.4.3 | None | Reflect, replan, or resume |
| Audit persistence | G2.4.5 observer | Pass exact observer binding only | Write or query audit evidence |

### Future contracts and refusal behavior

**RECOMMENDATION.** Define a narrow `GovernedRuntimeExecutor` protocol with one `execute(GovernedExecutionRequest) -> GovernedExecutionResult` operation. Define a `ControlledRuntimeInvocationRequest` as an immutable wrapper around only the already-published session inputs and executor. Define an `InvocationDecision` that distinguishes `RUNTIME_INVOKED`, `SESSION_REFUSED`, and `RUNTIME_FAILED_AFTER_CONSUMPTION` without exposing a retry handle.

The permit must be consumed before dispatch. Therefore a runtime exception, audit persistence exception, or terminal failure does not cause an invoker retry and does not return a new session. This is a fail-closed decision: a caller may observe the exception/result and audit evidence, but cannot replay the same activation receipt or session.

### Deterministic benchmark roadmap

**RECOMMENDATION — EBS-022: Controlled Runtime Invocation.** The next deterministic benchmark should use a counting fake runtime, a counting audit-observer double, an approved activation fixture, and the published session gate. It must prove the following.

| Scenario | Required proof |
|---|---|
| Valid controlled dispatch | Activation admitted → session created → permit consumed → exact runtime request dispatched once → terminal fake result returned |
| Missing/denied activation | Runtime call count remains zero |
| Session replay or cross-gate receipt replay | Runtime call count remains zero |
| Changed request/policy/isolation/audit binding | Runtime call count remains zero and typed session refusal is preserved |
| Runtime unavailable | Runtime call count remains zero |
| Runtime raises after dispatch | Exactly one runtime call; no second call, retry, replacement session, or continuation authority |
| Observer non-execution by invoker | Invoker makes no direct observer method call; the fake runtime alone may demonstrate its own existing observer behavior |
| Safety | `REAL_PROVIDER_CALLS=0`, `WORKSPACE_MUTATIONS=0`, `GIT_MUTATIONS=0`, `SHELL_INVOCATIONS=0`, `NETWORK_INVOCATIONS=0`, `CREDENTIAL_ACCESS=0` |

A later provider-readiness benchmark should remain separate. It should not be classified as EBS-022 and should never be run automatically by the deterministic suite.

### Migration and non-goals

G2.4.7.1 should be additive. No existing direct G2.4.4 caller, CLI command, autonomous loop, Chief/Coordinator composition, capability path, or approval manager call site should migrate. The new invoker is an explicit library-only option for a future caller who intentionally supplies the exact published bindings.

The milestone must not create a persistent workspace, retain sessions across restart, add pause/resume, add a provider, add new capability types, alter audit storage, remove activation/session checks, or expose runtime execution through the CLI. It must not convert an audit record into a continuation artifact.

## Definition of done for a future G2.4.7.1 implementation

A future implementation is ready for review only when it satisfies all of the following deterministic criteria.

| Requirement | Acceptance evidence |
|---|---|
| One explicit non-legacy invoker exists | Unit/import-isolation coverage proves no CLI/autonomous migration |
| Runtime dispatch follows session consumption | EBS-022 exact call-order and call-count assertions |
| No second execution authority | Invoker delegates exactly once and does not manipulate context/state/budgets |
| No replay/retry/continuation | Reused session, receipt replay, and runtime failure all refuse future dispatch |
| Audit observation remains runtime-owned | Invoker does not call the observer directly |
| No provider/live execution | Deterministic fake only; explicit counters remain zero |
| No workspace lifecycle expansion | Disposable fixtures only; no create/copy/delete/cleanup implementation |
| Compatibility is preserved | G2.4.1–G2.4.6.2 regression and autonomous suites remain green |

## Conclusion

**FACT.** The published system now defines a careful admission and single-use handoff perimeter but does not yet use it to call the existing runtime.
**INFERENCE.** The smallest remaining deterministic safety gap is invocation sequencing, not provider capability, recovery, or human pause/resume.
**RECOMMENDATION.** Authorize a separate G2.4.7.1 implementation only if its scope is restricted to the controlled session invoker and deterministic EBS-022 described above. Keep live providers, CLI migration, persistent workspaces, durable human intervention, and capability expansion explicitly out of scope.

## References

[1]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/governed_runtime/runtime.py "Published G2.4.4 governed runtime"
[2]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/governed_activation/admission.py "Published G2.4.6.1 activation admission"
[3]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/governed_session/gate.py "Published G2.4.6.2 controlled session gate"
[4]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/docs/architecture/G2.4_GOVERNED_ENGINEERING_EXECUTION_LOOP.md "G2.4 architecture"
[5]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/governed_audit/recorder.py "Published G2.4.5 audit recorder"
[6]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/governed_audit/query.py "Published audit query and continuation rejection"
[7]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/approval/manager.py "Published approval lifecycle manager"
[8]: https://github.com/MenaYassa/EAG/blob/v2.4.6.2-g2.4.6.2/src/eag/benchmark/fixtures.py "Published disposable benchmark workspace fixture"
