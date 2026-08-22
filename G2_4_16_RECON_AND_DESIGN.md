# G2.4.16 — Governed External Transition Authorization Evidence Reconnaissance and Design

**Status:** Design only. **Published baseline:** `66cb5a1a0f77844593b3a3ec77c5b9a1d2486cc3`, tagged `v2.4.15-g2.4.15`.

> **Recommendation:** The safest next milestone is **G2.4.16 — Governed External Transition Authorization Evidence Boundary**. It should be a library-only, immutable, read-only assessor of an explicit human transition-decision record bound to one exact G2.4.15 `ELIGIBLE` assessment and declared transition intent. It must not issue a permit, create a session, claim idempotency, contact a destination, access credentials, execute a transition, or record that an external transition occurred.

## 1. Decision summary

| Question | Conclusion |
|---|---|
| What is missing after READY artifact plus ELIGIBLE transition? | An exact, explicit, human-governed authorization evidence binding for an irreversible **external** transition. G2.4.15 establishes technical eligibility only; it does not express an operator’s decision about an external side effect. |
| Is an artifact transition executor safe now? | **No.** The repository lacks a governed destination client/registry abstraction, credential and egress boundary, transition-specific approval consumption, durable idempotency claim, destination-side verification, external receipt, and recovery semantics. |
| What is the recommended next boundary? | **G2.4.16 external transition authorization evidence validation**, not an executor. |
| Does G2.4.16 create approval or transition authority? | **No.** It validates supplied explicit decision evidence and returns an immutable evidence assessment. A future executor, separately designed and approved, would own evidence consumption and any irreversible side effect. |
| Is external destination attestation the better first step? | **No.** G2.4.15 already defines bounded logical destination identities. Attesting live destination capability requires egress and credential/destination access that have no safe owner yet. |

## 2. FACT — repository-supported capabilities and absences

G2.4.14 represents immutable artifact readiness evidence. It binds an artifact identifier and exact fingerprint to supplied snapshot, packaging, external validation receipt, and hygiene evidence; `READY` is explicitly evidence-only and grants no execution or publication capability.[1]

G2.4.15 represents immutable transition eligibility evidence. It consumes G2.4.14 evidence and validates a declared lineage, exact artifact identity/fingerprint, logical destination identity, and promotion profile. Its assessor has no workspace, provider, credential, network, upload, registry, release, deployment, mutation, audit-write, or retry dependency; `ELIGIBLE` does not perform or record a transition.[2]

G2.4.6.1/G2.4.9/G2.4.6.2-G2.4.8/G2.4.7.1 retain the published activation, session-oriented human approval, replay, and invocation boundaries. The G2.4.9 approval receipt is bound to a prospective governed runtime session and its runtime/activation/isolation context. It is not a release- or destination-specific transition authorization and cannot safely be repurposed as one.[3]

The repository contains a generic `CommandExecutor` that can use subprocess execution and inherited environment variables. That legacy execution component is neither a registry client nor a governed external-transition boundary and must not be used for artifact publishing or deployment.[4] Existing context sensitivity logic redacts selected secret-like content when reading repository context, but it is not a credential acquisition, storage, rotation, or outbound egress-control system.[5]

The generic safety rollback engine rolls checkpoints through an injected checkpoint backend. It does not model external registry rollback, artifact unpublication, deployment reversal, destination idempotency, or external-state reconciliation.[6] The inspected repository contains no concrete artifact-registry abstraction, package publishing interface, upload client, deployment abstraction, release executor, CI/CD release lane, secret manager, registry credential boundary, egress allowlist, external transition receipt, or destination verification client.[7]

## 3. Inferred gap before an external transition

The current control plane can say:

```text
G2.4.14: exact artifact evidence is READY
G2.4.15: exact artifact/destination intent is ELIGIBLE
```

It cannot say that a human explicitly authorized that particular irreversible transition, nor can it safely infer authorization from the pre-session approval. The missing evidence must bind every consequential fact: artifact fingerprint, G2.4.15 assessment digest, declared destination identity, transition intent/policy digest, decision identity, operator identity, bounded authorization lifetime, and future receipt expectations.

No existing boundary provides safe external idempotency. A key can be declared and bound as evidence, but its global consumption must be owned by a later durable transition executor because it describes external state and requires atomic claim/reconciliation with a destination. Similarly, no current contract can prove “transition happened”: that requires a later destination-aware executor and a verified external receipt.

## 4. Failure and risk analysis

| Future external failure | Current protection | Missing control before executor design | Why G2.4.16 helps, but does not solve the transition |
|---|---|---|---|
| Partial upload | None; no upload path exists | Destination-aware idempotency, receipt verification, reconciliation, recovery policy | Binds an operator decision to exact intent; does not claim recovery capability. |
| Duplicate publication | No transition identity or durable consumption domain exists | External idempotency key and atomic durable claim tied to destination semantics | Defines a canonical declared transition key for later binding; does not consume it. |
| Interrupted transition | G2.4.8 protects sessions, not external state | Durable transition state, reconciliation, retry/abort policy | Ensures no automatic retry becomes authorized by generic evidence. |
| Destination unavailable | No destination client exists | Egress, health/attestation, bounded failure policy | Keeps unavailable-destination handling out of an evidence boundary. |
| Wrong artifact pushed | G2.4.14/15 bind artifact identity locally | Executor must verify exact identity against a destination-side request/receipt | Binds authorization to the exact readiness/eligibility artifact fingerprint. |
| Credential failure/exposure | Context redaction only | Credential broker, least privilege, isolated secret handling, egress policy | Excludes credentials entirely from authorization evidence. |
| External verification mismatch | No external receipt type or verifier exists | Destination receipt schema and verification logic | Requires a future design; G2.4.16 must not synthesize a receipt. |
| Rollback/unpublish | Generic checkpoint rollback only | Destination-specific compensating action and release policy | Explicitly defers all rollback authority. |

## 5. Candidate comparison

| Candidate | Value | Principal risk | Recommendation |
|---|---|---|---|
| **A. Artifact transition executor** | Could eventually perform publish/upload/deploy. | Combines credentials, egress, registry semantics, irreversible effects, idempotency, external receipts, reconciliation, and rollback into an unprepared new authority. | Defer. |
| **B. External destination attestation** | Could eventually declare target environment/registry readiness. | A truthful attestation needs destination access, external probes, credential handling, and freshness semantics. | Defer until destination/egress design exists. |
| **C. External transition authorization evidence boundary** | Adds the missing human-governance evidence step while remaining entirely read-only and deterministic. | Could be misread as a permit if terminology is not precise. | **Recommend.** Output must be evidence validity only, never a permit or executor command. |
| **D. Transition receipt/evidence boundary** | Needed after a real transition to record outcome. | Without a transition executor it would create a misleading synthetic “happened” record. | Defer; pair with a future executor and external verifier. |
| **E. Provenance strengthening** | Could later establish a fuller lifecycle lineage. | Cannot yet establish external destination causality and could overclaim producer/destination facts. | Defer beyond the narrow bindings required by Candidate C. |
| **F. Rollback/recovery boundary** | Needed for irreversible external actions. | Recovery semantics are destination-specific; no external operation exists to recover. | Defer until after a transition executor and receipt model are designed. |

## 6. Recommendation — G2.4.16 scope

### 6.1 Purpose

G2.4.16 should answer only:

> “Is supplied explicit human transition-decision evidence correctly bound to this exact G2.4.15 eligible transition intent, under a declared authorization policy, without claiming that the transition will or did occur?”

It should use **authorization evidence** rather than a session permit. A later external transition executor must remain the only component that can consume valid authorization evidence, obtain credentials, call a destination, claim idempotency, and emit an external receipt.

### 6.2 Proposed contracts

| Contract | Inputs and purpose | Forbidden capability |
|---|---|---|
| `ExternalTransitionIntentEvidence` | Immutable intent ID; artifact ID/fingerprint; G2.4.15 eligibility assessment ID/digest; logical destination identity; declared transition class; declared idempotency key; policy digest; expected external receipt schema/version. It contains no URL, client, credential, upload configuration, or payload bytes. | No destination connection, idempotency claim, upload, release, or deployment. |
| `ExternalTransitionAuthorizationEvidence` | Immutable externally captured human decision evidence: decision ID, operator identity, approve/deny disposition, timestamp/expiry, exact intent digest, eligibility assessment digest, authorization policy digest, and binding digest. The G2.4.16 validator validates it; it does not decide on behalf of a human. | No session/permit issuance, approval reservation, or executor dispatch. |
| `ExternalTransitionAuthorizationAssessment` | Immutable output with `VALID_AUTHORIZATION_EVIDENCE`, `NOT_AUTHORIZED`, or `UNSUPPORTED_TRANSITION_PROFILE`; findings, evidence references, recommendations, timestamp, and canonical digest. | No `authorize`, `execute`, `transition`, `upload`, `publish`, `deploy`, `retry`, `rollback`, or receipt method. |

### 6.3 Ownership map

| Concern | Current / future owner | G2.4.16 role |
|---|---|---|
| Artifact readiness | G2.4.14 | Consume exact READY evidence indirectly through G2.4.15. |
| Promotion eligibility | G2.4.15 | Consume exact ELIGIBLE assessment and intent binding. |
| Human transition decision | Human/external decision capture system; future release-governance owner | Validate a supplied immutable decision binding only; do not create a decision. |
| Authorization evidence validity | **G2.4.16** | New read-only evidence-validation owner. |
| Session/permit / invocation | G2.4.6.2/G2.4.8 and G2.4.7.1 | Unchanged and not used as a release permit. |
| Credentials and egress | Future credential/egress boundary | Not present. |
| Idempotency claim and destination state | Future external transition executor | Not present; G2.4.16 only binds a declared key. |
| External transition receipt and verification | Future executor/verifier | Not present. |
| Rollback/reconciliation | Future destination-specific recovery owner | Not present. |

### 6.4 Validation and failure matrix

| Condition | Required result | Example finding |
|---|---|---|
| Exact G2.4.15 assessment is missing, non-ELIGIBLE, corrupt, or its digest differs | `NOT_AUTHORIZED` | `ELIGIBILITY_EVIDENCE_INVALID` |
| Intent artifact/destination/policy or eligibility binding differs | `NOT_AUTHORIZED` | `TRANSITION_INTENT_BINDING_MISMATCH` |
| Authorization decision is denied, expired, missing, altered, or bound to a different intent/assessment | `NOT_AUTHORIZED` | `TRANSITION_AUTHORIZATION_INVALID` |
| Declared idempotency key missing or malformed | `NOT_AUTHORIZED` | `IDEMPOTENCY_KEY_INVALID` |
| External receipt schema or transition class unsupported | `UNSUPPORTED_TRANSITION_PROFILE` | `UNSUPPORTED_TRANSITION_PROFILE` |
| Destination identity includes URL, credential, authentication material, or upload configuration | `NOT_AUTHORIZED` | `DESTINATION_IDENTITY_INVALID` |
| Any upload, registry response, deployment state, network observation, or credential is absent | No transition inference | No synthetic receipt or authorization-to-execute result. |

## 7. EBS-031 proposal

**EBS-031: External Transition Authorization Evidence** must be a deterministic evidence-only benchmark using G2.4.14 and G2.4.15 public contracts plus fixed synthetic authorization evidence. It must not create a package, run a command, call a registry, create a network client, access credentials, or mutate a workspace/repository.

| Scenario | Required direct assertion |
|---|---|
| Exact eligible artifact transition plus valid explicit operator decision evidence | `VALID_AUTHORIZATION_EVIDENCE`; all artifact, eligibility, intent, policy, destination, and idempotency-key bindings match. |
| Missing/non-ELIGIBLE/altered G2.4.15 evidence | `NOT_AUTHORIZED`. |
| Altered artifact fingerprint, destination, eligibility digest, or transition intent | `NOT_AUTHORIZED`. |
| Denied, expired, altered, or mismatched authorization evidence | `NOT_AUTHORIZED`. |
| Invalid idempotency key | `NOT_AUTHORIZED`; no durable claim occurs. |
| Unsupported transition or receipt profile | `UNSUPPORTED_TRANSITION_PROFILE`. |
| Side-effect guard | Provider calls, uploads, registry/deployment calls, command executions, network activity, credential access, workspace/repository mutation, runtime calls, session/permit issuance, and audit writes are all zero. |

## 8. Explicit non-goals

G2.4.16 must not upload artifacts; publish packages; create releases; deploy applications; contact registries or external services; create registry clients; store/access/rotate credentials; introduce egress; invoke providers or runtimes; create sessions or permits; modify/copy/move/clean artifacts; mutate repositories/workspaces; consume idempotency keys; retry, rollback, reconcile, or recover transitions; emit external transition receipts; modify G2.4.14/G2.4.15 ownership; expose CLI actions; or migrate autonomous paths.

## 9. Acceptance criteria for a future implementation

A future G2.4.16 implementation is acceptable only if it introduces one isolated evidence-only package with frozen contracts, canonical digests, exact eligibility/intent/decision binding, expiry and denial refusal, typed fail-closed findings, and EBS-031. It must not import into or modify any existing runtime/control owner except for public evidence type references. The new package must have no dependency on subprocesses, network libraries, destination clients, credential stores, workspace mutation, provider execution, or release automation.

## 10. Reconnaissance disposition

```text
G2.4.16_RECON=COMPLETE
G2.4.16_DESIGN=COMPLETE
G2.4.16_IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
BENCHMARK_CHANGES=0
REAL_PROVIDER_CALLS=0
UPLOAD_CALLS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
WORKSPACE_MUTATIONS=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```

## References

[1]: ./src/eag/governed_artifact_readiness/models.py "G2.4.14 artifact readiness contracts"
[2]: ./src/eag/governed_promotion/assessor.py "G2.4.15 promotion eligibility assessor"
[3]: ./src/eag/governed_approval/models.py "G2.4.9 session-oriented human approval receipt"
[4]: ./src/eag/execution/executor.py "Generic subprocess command executor"
[5]: ./src/eag/context/sensitivity.py "Repository-context sensitivity redaction"
[6]: ./src/eag/safety/rollback.py "Generic checkpoint rollback engine"
[7]: ./pyproject.toml "Published EAG packaging and dependency configuration"
