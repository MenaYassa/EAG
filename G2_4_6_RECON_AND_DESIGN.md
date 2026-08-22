# G2.4.6 Reconnaissance and Design — Controlled Governed Activation

**Design date:** 22 August 2026
**Published baseline:** [`v2.4.5-g2.4.5`](https://github.com/MenaYassa/EAG/tree/v2.4.5-g2.4.5) at `c82db4a0f309f1e503834e6eaa901c15d2f2c4ba`
**Scope:** Analysis and architecture only
**Author:** Manus AI

> **Decision.** The recommended G2.4.6 direction is **controlled governed activation**: an explicit, non-default composition and activation boundary that prepares a governed run only when trusted configuration, caller confirmation, workspace isolation, and required audit observation are all present. It should neither introduce production-default execution nor call a real provider by default.

## 1. Current Architecture Facts

**FACT.** G2.4.1–G2.4.5 form an evidence-first governed path distinct from the legacy autonomous path. The state machine owns legal transitions, immutable execution history, budgets, and terminality; verification remains distinct from mutation postcondition; reflection/replanning remains bounded and freshness-checked; the G2.4.4 runtime is the sole serial orchestrator; and G2.4.5 observes completed contexts through a redacted, integrity-checked audit projection.[1] [2]

**FACT.** The governed gateway is deliberately advisory. It routes a structured request, applies timeout/attempt and token/cost policy, parses schema output, validates deterministic policy, and returns either a validated `EngineeringDecisionResult` or a classified safe failure. It does not write a workspace.[3]

**FACT.** The published `build` command still deletes/recreates a chosen workspace and invokes the legacy `AutonomousLoopRuntime`; it does not expose any governed-runtime activation path.[4] The existing gateway configuration is explicitly disabled by default and already provides provider/model, secret, endpoint, timeout, attempt, token, estimated-cost, and fallback settings.[5]

**FACT.** G2.4.5's local file store provides deterministic append/load integrity and rejects audit roots in or below the subject workspace. It is not a database, multi-user service, authenticated operator record, cross-process lock, or availability mechanism.[2]

## 2. Completed Milestone Inventory

| Milestone | Published capability | Authority retained outside the milestone |
|---|---|---|
| G2.4.1 | Immutable governed context, legal state machine, append-only ledger, budgets, stop reasons. | Mutation, provider, verification, reflection, and CLI execution. |
| G2.4.2 | Deterministic verification specification/result and objective-completion separation. | File mutation and execution transition ownership. |
| G2.4.3 | Reflection, provenance-bound memory evidence, replanning, full-iteration freshness. | New decision/proposal/authorization creation. |
| G2.4.4 | Explicit two-iteration serial governed runtime with a one-attempt/no-fallback request policy. | Legacy autonomous and CLI topology. |
| G2.4.5 | Immutable redacted durable audit envelope, canonical file store, integrity checks, query, interruption rejection. | Lifecycle transition, resume, retry, replay, provider, mutation, verification. |

> **FACT.** The published G2.4 architecture file retains a historical status banner that predates G2.4.4 and G2.4.5 publication. The release tags and source contracts, rather than that banner, are the authoritative current-state evidence for this reconnaissance.[1] [2]

## 3. Remaining Capability Gaps

### 3.1 Real-provider readiness

**FACT.** Gateway policy has deterministic controls for attempts, timeout, token/cost ceilings, and fallback. Provider transport failure, timeout, schema invalidity, policy rejection, and budget exceedance return classified failure results and emit events.[3]

**FACT.** EBS-014 is an opt-in live advisory benchmark. It requires explicit environment activation and credentials, constrains the gateway to one attempt and no fallback, uses a fixed cost/token cap, and prohibits capability, workspace, Git, shell, commit, and push effects.[6] Historical live observations establish neither provider availability nor reliable policy-compliant repository decisions as a production readiness result.

**INFERENCE.** The technical gateway boundary is sufficient for a controlled experiment but not for controlled governed execution. There is no published composition that binds an activated provider configuration, explicit caller intent, a segregated workspace, a required audit observer, cost visibility, and a terminal operator outcome in one trusted request.

**RECOMMENDATION.** Treat real-provider execution as a future controlled lane, never as an implication of gateway enablement. G2.4.6 should establish the trusted activation boundary first; a separate live benchmark may exercise that boundary only after explicit later authorization.

### 3.2 Production activation readiness

| Readiness concern | FACT | Gap | Recommendation |
|---|---|---|---|
| Explicit opt-in | Gateway settings have `enabled=False`; EBS-014 uses environment opt-in.[5] [6] | No governed-run activation contract. | Require an immutable `GovernedActivationRequest` with caller confirmation and policy fingerprint. |
| API/CLI boundary | `build` is legacy autonomous only.[4] | No additive governed command/API surface. | Define a library composition first; defer CLI exposure until its safety contract is tested. |
| User authorization | G2.3.1 authorization binds a mutation to a proposal. | No caller intent binding for a governed trajectory. | Require an activation attestation distinct from mutation authorization. |
| Environment isolation | Audit root must be outside the subject workspace.[2] | No activation-level workspace creation/ownership rule. | Require a caller-supplied isolated workspace identity and audit root before composition. |
| Rollback | G2.3.1 handles bounded file postcondition rollback. | No whole-run rollback/replay promise. | Do not promise trajectory rollback; retain only per-mutation semantics and audited terminal outcomes. |
| Audit visibility | G2.4.5 supplies a local queryable terminal record.[2] | No operator-facing activation receipt or audit-location contract. | Return only redacted activation/audit identifiers and fail before execution if required audit preparation fails. |

### 3.3 Human governance layer

**FACT.** The existing approval store is in-memory and supports request status transition only. Legacy `AutonomousLoopRuntime` has its own pause/resume path, but that path has no binding to G2.3.1 proposal authorization or G2.4 evidence.[7] [1]

**INFERENCE.** Introducing governed pause/resume next would require durable approval identity, expiry, actor authentication, proposal-digest binding, audit linkage, and a new execution re-entry contract. That conflicts with G2.4.5's explicit non-resumable interruption posture and would expand lifecycle authority substantially.

**RECOMMENDATION.** Do not make human pause/resume the next implementation milestone. Reserve a future governance direction for a **pre-authorization, terminal-only approval decision** bound to a proposal digest; it must never resume an interrupted execution or stand in for mutation authorization.

### 3.4 Capability expansion

**FACT.** The current governed mutation path is intentionally one bounded file mutation per iteration. The provider prompt and policy reject arbitrary shell, Git, network, credential, or extra-mutation behavior.[3]

**INFERENCE.** Multi-file change sets, test execution, builds, and repository operations would require separate trusted capability specifications, input/output redaction, authorization semantics, bounded side-effect models, rollback limits, and audit evidence. Adding any of them before activation control would multiply the blast radius without proving a safe entry point.

**RECOMMENDATION.** Preserve the current capability set. Defer test/build capability design until a later milestone after controlled activation and governed human authorization are independently established.

### 3.5 Benchmark maturity and security

**FACT.** EBS-016 through EBS-019 cover deterministic state/verification, replanning/freshness, serial composition, and durable audit integrity. EBS-014 remains a separately opt-in live advisory benchmark; EBS-015 includes deterministic mutation coverage but has unresolved historical live evidence.[6] [1]

**INFERENCE.** The largest missing benchmark is not a larger fixture or a third iteration. It is a deterministic proof that activation fails closed before provider/mutation work when any activation precondition is absent, and that a valid activation produces a redacted audited terminal result through the existing governed path.

**RECOMMENDATION.** Add an activation EBS only after a narrow activation contract exists. Keep larger fixtures, multi-failure matrices, adversarial approval, and real-provider scenarios as later test plans rather than scope additions.

## 4. Candidate Milestone Directions

| Direction | Value | Principal risk | Scope fit | Recommendation |
|---|---|---|---|---|
| **A. Controlled governed activation** | Creates the safety gate needed before any deliberate provider-backed governed run. | Incorrect activation could expose mutation authority too broadly. | Narrow if activation is composition-only and explicit. | **Recommended.** |
| B. Human approval/pause/resume | Adds human governance. | Requires durable actor/expiry/proposal binding and conflicts with non-resumable interruptions. | Broad. | Defer. |
| C. Capability expansion | Enables tests, builds, multi-file, or repository operations. | Multiplies authority and rollback/security models. | Broad. | Defer. |
| D. Live-provider retry/reliability | May improve availability experimentation. | Risks confusing provider variance with safe execution and creating retry semantics. | Unsafe as a default. | Defer. |
| E. Audit service/UI | Improves operational visibility. | Introduces remote identity, access control, and retention concerns. | Broad. | Defer. |

## 5. Risk Ranking

| Rank | Risk | Why it matters | Required control before broader activation |
|---|---|---|---|
| Critical | Accidental entry from legacy CLI/autonomous path | Could bypass the explicit governed composition and its audit preconditions. | Separate public activation boundary; no `build` migration. |
| Critical | Provider output inducing unauthorized effect | Provider text is untrusted even when structured. | Existing schema/policy/translation/authorization chain remains mandatory. |
| Critical | Interrupted mutable run mistaken for resumable work | Can duplicate provider, authorization, or mutation effects. | Continue G2.4.5 interruption rejection; no continuation token. |
| High | Audit unavailable or placed in subject workspace | Could lose an observable record or create an unsafe second write surface. | Required audit preflight and separate explicit audit root. |
| High | Misconfigured provider cost/retry/fallback | Can exceed the intended controlled-run boundary. | Fixed one-attempt/no-fallback activation policy and immutable ceilings. |
| High | Approval conflated with mutation authorization | Would weaken proposal-bound one-time authorization. | Separate future approval binding and no authorization reuse. |
| Medium | Capability expansion without trusted specifications | Adds shell/Git/network or multi-file side effects without governance. | Defer; add each capability as a separate authority model. |
| Medium | Audit tampering or insufficient operator identity | Limits confidence in local audit evidence. | Existing digest detects local tamper; defer signatures/access control to a later operational milestone. |

## 6. Recommended Next Milestone

### G2.4.6 — Controlled Governed Activation Boundary

**RECOMMENDATION.** Implement a new explicit opt-in library composition that can construct one G2.4.4 governed runtime only after validating activation preconditions. It is an admission-control boundary, not a second lifecycle controller and not a provider/runtime rewrite.

The activation sequence would be:

```text
caller-supplied isolated workspace + separate audit root
    + explicit activation confirmation
    + fixed governed provider policy
    + available trusted composition dependencies
        -> activation validation
        -> explicit G2.4.4 runtime composition with mandatory G2.4.5 observer
        -> caller invokes existing bounded runtime
        -> terminal redacted audit query/receipt
```

**RECOMMENDATION.** The first implementation must be deterministic. It may use scripted gateway and real existing G2.3.1/G2.3.2/G2.4.1–G2.4.5 components, but it must not enable `build`, rewrite legacy runtime composition, make a live provider call, or add a production CLI command.

## 7. Safety Constraints

The following must remain non-negotiable:

```text
DEFAULT_GOVERNED_ACTIVATION=DISABLED
LEGACY_AUTONOMOUS_PATH=UNCHANGED
ONE_PROVIDER_ATTEMPT_PER_GOVERNED_ITERATION=MAXIMUM
FALLBACK=DISABLED_FOR_CONTROLLED_ACTIVATION
AUTOMATIC_PROVIDER_RETRY=DISABLED
MUTATION_AUTHORIZATION=G2.3.1_ONLY
EXECUTION_LIFECYCLE=G2.4.1_AND_G2.4.4_ONLY
AUDIT_OBSERVER=G2.4.5_ONLY
AUDIT_ROOT_OUTSIDE_SUBJECT_WORKSPACE=REQUIRED
RESUME_REPLAY_RETRY=PROHIBITED
SHELL_GIT_NETWORK_CAPABILITIES=NOT_ADDED
RAW_PROVIDER_OUTPUT_CREDENTIALS_FILE_CONTENT=AUDIT_PROHIBITED
```

**FACT.** These constraints preserve the validated separation in the published milestone contracts.[1] [2] [3]

## 8. Required Contracts If Implementation Proceeds

| Contract | Purpose | Must not do |
|---|---|---|
| `GovernedActivationRequest` | Immutable caller intent: workspace root, audit root, execution/run IDs, provider policy profile ID, and explicit confirmation. | Carry provider credentials, raw goal/context data beyond existing request contracts, or an authorization token. |
| `GovernedActivationPolicy` | Pure validator for enabled setting, isolated paths, fixed one-attempt/no-fallback policy, bounded token/cost/timeout values, and required audit observer. | Select lifecycle transitions, execute gateway calls, or mutate a workspace. |
| `GovernedActivationReceipt` | Redacted immutable outcome: activation ID, execution ID, policy digest, audit location identity, and accepted/refused reason. | Signal mutation success or replace terminal audit evidence. |
| `create_controlled_governed_activation(...)` | Explicit composition factory returning the existing G2.4.4 runtime plus observer after validation. | Be called from legacy autonomous factory or CLI by default. |
| `GovernedActivationRefused` | Typed refusal for unsafe/missing preconditions before any provider, authorization, or mutation work. | Trigger retries, fallback, or partial composition. |

**RECOMMENDATION.** No contract should accept raw provider credentials. Credential resolution must stay inside the existing explicit gateway-settings composition and never enter audit envelopes or activation receipts.

## 9. Benchmark Proposal

### EBS-020 — Controlled Governed Activation

The deterministic EBS should use a disposable subject workspace, a distinct disposable audit root, a scripted gateway, and the real G2.3.1/G2.3.2/G2.4.1–G2.4.5 governed components.

| Scenario | Required proof |
|---|---|
| Valid controlled activation | Explicit confirmation and fixed policy compose the existing bounded runtime; two-iteration fixture completes; terminal audit record reloads through a fresh query instance. |
| Activation disabled | Typed refusal occurs before gateway, authorization, mutation, verification, or audit record write. |
| Missing confirmation | Typed refusal with all operational counters at zero. |
| Audit root equals/is below subject workspace | Typed refusal with all operational counters at zero. |
| Retry/fallback or unbounded policy requested | Typed refusal; activation must not silently normalize unsafe values. |
| Interrupted audit record supplied as context | Typed refusal; no resume, replay, third iteration, or authorization reuse. |
| Terminal audit write failure | Existing explicit audit persistence failure remains distinct from mutation failure and triggers no re-execution. |

The benchmark must report:

```text
REAL_PROVIDER_CALLS=0
CAPABILITY_EXECUTIONS=0
SHELL_INVOCATIONS=0
GIT_MUTATIONS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
EAG_SOURCE_WORKSPACE_MUTATIONS=0
NO_LEGACY_AUTONOMOUS_PATH=PASS
NO_AUTHORIZATION_REUSE=PASS
NO_RESUME_OF_NONTERMINAL_EXECUTION=PASS
```

A later, separately authorized **EBS-020-LIVE** may test a single advisory provider decision under an immutable fixed policy. It must not be necessary for deterministic implementation completion and must not mutate the source repository.

## 10. Migration Strategy

1. **No migration in the first G2.4.6 implementation.** Retain the legacy CLI and autonomous factory without import or behavior changes.
2. **Add the library boundary behind explicit caller construction.** Existing tests and applications remain untouched unless they opt in.
3. **Validate deterministic activation.** Require EBS-020, G2.4.1–G2.4.5 regressions, autonomous regression, full deterministic suite, scoped static checks, and scope-isolation checks.
4. **Review the activation contract before any CLI/API exposure.** A later decision may add an explicit command or API only with user confirmation, environment isolation, audit query access, and an approved live-test plan.
5. **Keep live operation independently authorized.** A configured gateway is necessary but insufficient; each controlled live evaluation must have its own approval.

## 11. Non-Goals

G2.4.6 should not implement production-default activation, CLI migration, AutonomousLoopRuntime changes, Chief/Coordinator changes, generic capability integration, human pause/resume, approval UI, provider retries/fallback, live-provider calls, multi-file mutation, test/build/shell/Git/network capability, audit-service deployment, multi-user access control, remote telemetry, database persistence, replay, or interruption resumption.

## 12. Definition of Done

G2.4.6 should be considered implementation-complete only when all of the following hold:

| Category | Required evidence |
|---|---|
| Activation authority | Unsafe requests are refused before any operational component is reached. |
| Boundary preservation | G2.4.1, G2.3.1, G2.3.2, G2.4.2, G2.4.3, G2.4.4, and G2.4.5 retain their published authorities. |
| Explicit opt-in | No default caller, legacy CLI, autonomous factory, Chief, Coordinator, or capability runtime activates the governed path. |
| Policy controls | One attempt, no fallback, bounded timeout/token/cost, workspace/audit separation, and explicit confirmation are validated deterministically. |
| Auditability | Every activated terminal run requires the existing redacted audit observer and exposes only read-only audit identifiers. |
| Benchmark | EBS-020 standalone passes with all side-effect counters at zero except permitted disposable governed fixture mutation. |
| Regression | G2.4.1–G2.4.5, autonomous, and full deterministic suites pass; Ruff, MyPy, and whitespace checks pass. |
| Publication discipline | No live-provider benchmark is run or claimed without explicit separate authorization. |

## References

[1]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/docs/architecture/G2.4_GOVERNED_ENGINEERING_EXECUTION_LOOP.md "G2.4 Governed Engineering Execution Loop architecture"
[2]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/G2_4_5_IMPLEMENTATION_REPORT.md "G2.4.5 implementation report"
[3]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/src/eag/chief/intelligence/gateway/runtime.py "Governed gateway runtime"
[4]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/src/eag/cli.py "CLI build command"
[5]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/src/eag/config/settings.py "Gateway settings"
[6]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/tests/test_ebs_014_repository_aware_decision.py "EBS-014 controlled live advisory benchmark"
[7]: https://github.com/MenaYassa/EAG/blob/v2.4.5-g2.4.5/src/eag/approval/store.py "Approval store"
