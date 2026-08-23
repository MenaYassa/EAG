# G2.4.19 Reconnaissance and Design — Governed External Outcome-Semantics Policy Evidence

**Status:** Reconnaissance and design only.
**Authoritative documentation baseline:** `3126eaf975820dd8ab1cbb7e9f8db868c237dad3`.
**Latest published engineering milestone:** `v2.4.18-g2.4.18` → `2606a1060f7341d269d5dfee5575c7a0d7050adb`.
**Authorized artifact:** This document only.

> **Recommendation:** The smallest legitimate next governance boundary is **G2.4.19 — Governed External Outcome-Semantics Policy Evidence Boundary**. It should be an isolated, immutable, deterministic, non-executable validator of supplied outcome-policy evidence bound to the exact G2.4.18 destination-contract evidence chain. It must define what a *future* executor and receipt verifier are allowed to classify as terminal, rejected-before-effect, or outcome-unknown, while requiring unknown outcomes to stop without automatic retry, reconciliation, rollback, release, or completion authority.

This recommendation is deliberately **not** an external executor, request builder, destination client, receipt verifier, credential boundary, egress boundary, reconciliation service, retry engine, rollback authority, or release/publication state owner. It adds no external operation path.

## 1. Executive finding

The published chain proves exact local evidence consistency through destination-contract evidence. It does **not** yet define the governed semantic meaning of an eventual external outcome. G2.4.18 binds a future receipt-schema identifier and declared destination idempotency profile, but it cannot say which future receipt classifications are acceptable, whether a missing or lost response may be retried, whether outcome-unknown is terminal for automatic progress, or whether a future receipt could be mistaken for external completion.[1]

The next safe work is therefore to bind **outcome semantics before execution exists**, not to introduce execution. A future executor must never decide at runtime that a timeout is harmless, a destination acknowledgement is final success, a retry is allowed, or a rollback is safe. Those are governance semantics that must be declared and fail closed in advance.

## 2. FACT — what the repository now proves

| Published boundary | Published authority | What it proves | What it does not prove |
|---|---|---|---|
| G2.4.14 — Artifact Readiness | Immutable artifact-readiness evidence | A supplied artifact snapshot, packaging/validation evidence, and hygiene evidence satisfy readiness conditions. | Destination acceptance, upload, release, or any external effect. |
| G2.4.15 — Promotion Eligibility | Logical-destination eligibility evidence | Exact artifact/readiness/lineage/policy evidence is eligible for a non-secret logical destination. | Endpoint selection, destination protocol, client, credential, request, or external receipt. |
| G2.4.16 — External Transition Authorization | Human authorization evidence | A supplied human decision is bound to the exact intent, artifact, destination, policy, execution/run identity, and expiry. | A permit, external request, receipt, retry, recovery, or executor authority. |
| G2.4.17 — Transition Control Ledger | Durable local duplicate/conflict/ambiguity control | A future external attempt has a durable local control identity; caller-only idempotency changes cannot bypass it. | Destination-side deduplication, permission, external completion, external receipt, retry, or reconciliation. |
| G2.4.18 — Destination Contract Evidence | Destination-facing contract evidence consistency | A supplied non-secret contract declaration exactly binds the authorized local chain to operation/request/receipt/idempotency *identifiers*. | Live destination truth, issuer trust, endpoint, credentials, egress, sendable request, receipt parsing, receipt authenticity, external verification, or outcome semantics. |

The published G2.4.18 assessor is pure: it consumes immutable evidence, returns immutable assessment evidence, and has no client, store, filesystem root, provider, credential, session, permit, runtime, executor, audit writer, or G2.4.17 ledger collaborator.[2] Existing invocation and session boundaries are scoped to a supplied governed runtime and its activation/session bindings, not to artifact transition requests, destination receipts, or external recovery.[3] Existing audit records are immutable observer projections of the governed execution lifecycle; they are not an external receipt store or reconciliation owner.[4]

## 3. FACT — intentionally absent capabilities

| Concern | Current state | Consequence |
|---|---|---|
| External request formation | No sendable request type or payload construction owner exists. | No component may form a destination request or infer that a declared request schema is executable. |
| Destination client and egress | No destination adapter, HTTP/registry client, connection factory, route allowlist, timeout owner, or transport policy exists. | No component may contact a destination. |
| Credential and account custody | No credential lease, account binding, authentication, signing, secret broker, rotation, or revocation authority exists. | No declared destination contract can be converted into authenticated access. |
| Contract-issuer trust | G2.4.18 validates only structural issuer/reference shape; no trust root, signature verifier, revocation owner, or policy selection authority exists. | A contract assessment is not a live or independently trusted destination attestation. |
| External receipt | No receipt payload contract, issuer verifier, destination query, or authoritative success classification exists. | No component may claim that an external effect occurred, completed, or was verified. |
| Outcome semantics | No owned vocabulary binds future receipt classes to retry, ambiguity, reconciliation, or completion rules. | A future executor could otherwise invent safety-critical outcome handling at execution time. |
| Reconciliation, retry, rollback | No destination effect, compensating action, receipt verifier, or external-state owner exists. | Outcome-unknown must remain terminal for automatic progress. |
| Release/publication state | No external lifecycle state exists. | Local evidence cannot become a release/publication completion record. |

## 4. Governance gap before external execution can ever be legitimate

A legitimate future external transition requires more than G2.4.14–G2.4.18 evidence. The remaining dependencies are independent and must not be collapsed:

```text
Published local evidence/control chain
        + trusted destination-contract source or policy owner
        + governed outcome-semantics policy
        + credential and account custody
        + egress/client authority
        + bounded external request formation and one-attempt executor
        + externally verifiable receipt evidence
        + explicit outcome-unknown / reconciliation authority
        → only then could an external operation be separately considered
```

The immediate semantic gap that can be closed safely now is the **outcome-semantics policy**. It is independent of live credentials, clients, and receipts, and it prevents those later components from assigning unsafe meaning to destination responses, timeouts, or missing responses.

The absence of a trusted contract-issuer owner remains a separate design dependency. G2.4.19 must not pretend that a policy declaration creates such a trust root. A later contract-trust-policy boundary will need an explicit owner and source of trust; it must not silently reuse G2.4.15 logical destination, G2.4.16 human transition authorization, or G2.4.17 control identity as a contract-selection authority.

## 5. Candidate G2.4.19 milestones

| Candidate | Purpose | Value | Primary risk | Decision |
|---|---|---|---|---|
| **A. Governed External Outcome-Semantics Policy Evidence** | Bind future outcome taxonomy, receipt-classification semantics, unknown-outcome stop rule, and no-automatic-retry rule to exact G2.4.18 evidence. | Prevents a future executor or verifier from inventing success, retry, rollback, or completion semantics at runtime. | Could be confused with an external receipt or reconciliation authority unless contracts exclude both explicitly. | **Recommended.** |
| B. Destination-contract trust-policy evidence | Define a trusted source for contract issuer/reference declarations. | Necessary before a real destination contract could be relied upon. | No current trust root, signature model, policy-selection owner, or revocation authority exists. Creating one now requires unresolved upstream governance design. | Defer; record as explicit dependency. |
| C. External request envelope | Bind an eventual sendable request to exact evidence. | Necessary immediately before a future external attempt. | Premature without credential, egress, account, transport, timeout, and receipt semantics; a sendable payload creates operational pressure. | Defer. |
| D. Credential/egress custody | Introduce least-privilege account and route controls. | Necessary before execution. | Broad secret/transport authority with no trusted contract source, request envelope, or account model. | Defer. |
| E. External receipt/verification boundary | Interpret an external receipt and verify destination-side result. | Necessary after a future attempt. | No operation, receipt issuer, verifier, query, or trust root exists. | Defer. |
| F. Reconciliation/retry/rollback boundary | Address uncertain external outcomes. | Necessary after external effects exist. | No external state, receipt, compensating action, or recovery owner exists; automatic retry would be unsafe. | Defer. |
| G. Destination executor/client | Perform an external operation. | Would produce a real side effect. | Combines every absent authority in one irreversible feature. | Reject. |
| H. Audit extension | Record an external outcome. | Might improve observability later. | G2.4.5 owns governed-execution observation, not external receipt truth or release state. | Reject as next step. |

## 6. Recommended G2.4.19 — Governed External Outcome-Semantics Policy Evidence Boundary

### 6.1 Narrow purpose

G2.4.19 should answer exactly one question:

> “Given an exact G2.4.18 attested destination-contract evidence chain and supplied immutable outcome-policy evidence, is the declared policy structurally valid and exactly bound to that chain, while requiring every future unknown outcome to stop without automatic retry, reconciliation, rollback, release, publication, deployment, or completion?”

The answer is evidence only. It neither observes an external outcome nor changes local durable state.

### 6.2 Authority owner and boundary

| Concern | Owner after proposed G2.4.19 | Boundary |
|---|---|---|
| Outcome taxonomy and automatic-stop semantics | **G2.4.19 outcome-semantics policy assessor** | Validate a supplied immutable policy declaration against exact G2.4.18 contract evidence and supported static profiles. |
| Artifact readiness | G2.4.14 | Unchanged; G2.4.19 consumes public evidence only. |
| Promotion eligibility and logical destination | G2.4.15 | Unchanged; no endpoint or contract selection is inferred. |
| Human transition authorization | G2.4.16 | Unchanged; no second human decision, permit, renewal, or extension. |
| Durable duplicate/conflict/ambiguity control | G2.4.17 | Unchanged; no claim/read/consume/reset/release/reconcile API. |
| Destination-contract evidence | G2.4.18 | Unchanged; G2.4.19 requires exact attested evidence but does not trust a contract issuer or select competing contracts. |
| External outcome/receipt truth | No owner yet | Explicitly deferred. G2.4.19 declares handling semantics only. |
| Reconciliation/retry/rollback | No owner yet | Explicitly deferred. G2.4.19 can require automatic stop but cannot perform, authorize, or plan recovery. |
| External audit or release state | No owner yet; G2.4.5 remains internal observer-only audit | Explicitly deferred. |

### 6.3 Proposed immutable public contracts

All proposed contracts must be frozen, slots-based, keyword-only, strictly typed, free of mutable public values and operational handles, canonically serialized, SHA-256 self-validating, schema-versioned, and UTC-normalized where time appears.

| Proposed contract | Canonically bound content | Explicit exclusions |
|---|---|---|
| `ExternalOutcomeSemanticsPolicyEvidence` | Policy ID; G2.4.18 contract ID/digest; G2.4.18 assessment ID/digest; logical destination; operation profile; receipt-schema identifier; destination-idempotency profile; declared outcome profile; supported future receipt-class taxonomy; `unknown_outcome_disposition=stop_and_reconciliation_required`; `automatic_retry=forbidden`; `automatic_rollback=forbidden`; `completion_requires_future_receipt_verification=true`; issued/expiry time; policy schema; canonical policy digest. | Receipt payload, response, endpoint, credential, secret, account, request payload, retry schedule, retry counter, client, callable, executor, release state, completion record, reconciliation command, rollback command, or external trust assertion. |
| `OutcomeSemanticsAssessmentRequest` | Exact immutable G2.4.18 assessment request, G2.4.18 destination-contract assessment, and one outcome-semantics policy declaration; optional immutable G2.4.17 decision evidence only for ambiguity stop. | G2.4.17 ledger object; G2.4.15–G2.4.18 re-evaluation/recreation; permit, session, runtime, executor, destination, audit, or store handle. |
| `OutcomeSemanticsFinding` | Typed deterministic policy/evidence reference and non-sensitive recommendation. | Destination response body, provider output, secret, future receipt body, or executable remediation. |
| `OutcomeSemanticsAssessment` | Assessment ID; exact destination and policy identity; disposition; immutable findings/recommendations/evidence references; canonical assessment digest; timestamp. | Permission, lease, reservation, claim, receipt, verification result, release/publication/deployment state, recovery authority, or outcome acknowledgement. |
| `OutcomeSemanticsAssessor` | Pure validation of supplied immutable evidence and supported static policy profile. | Networking, filesystem store, audit writer, G2.4.17 ledger, request formation, credential access, provider call, runtime dispatch, retry, reconciliation, or rollback. |

The proposed policy is a **declaration of required future handling**, not a statement that a receipt exists, that a destination honors the declaration, or that an external operation is safe. Its digest must include all its declared semantics and exact G2.4.18 evidence identifiers/digests. It must not add an unowned expected destination-contract ID; G2.4.18 contract ID remains declaration self-identity.

### 6.4 Canonical identity and digest semantics

The canonical policy identity must bind the exact destination-contract declaration and its positive evidence assessment. At minimum, the canonical payload must include:

```text
policy_id
schema_version
contract_id
contract_digest
contract_assessment_id
contract_assessment_digest
destination_identity
operation_profile
external_receipt_schema_id
destination_idempotency_profile
outcome_profile
receipt_class_taxonomy
unknown_outcome_disposition
automatic_retry_disposition
automatic_rollback_disposition
completion_verification_requirement
issued_at
expires_at
```

A policy assessment request digest must bind the supplied policy digest plus exact G2.4.18 request and assessment digests and, if supplied, the immutable G2.4.17 decision ID/digest/control key. The policy assessor must never calculate or consume the G2.4.17 control key and must never treat a `CLAIMED` decision as a permit.

Equivalent independently constructed evidence must reproduce identical canonical payloads and digests. An authoritative one-field variation must change the relevant policy/request digest and fail with the exact typed finding when that variation violates a required binding. Caller-only labels not used in the canonical authority must be either excluded from authoritative identity or retained as non-authoritative full-binding evidence; they may not create bypasses.

### 6.5 Deterministic validation order

1. Validate exact request types, immutability, schemas, timestamps, and self-digests.
2. Require the supplied G2.4.18 destination-contract assessment to be `CONTRACT_ATTESTED`; otherwise fail closed.
3. Validate exact contract ID/digest, destination, operation profile, receipt schema, and declared destination-idempotency profile against the G2.4.18 contract and assessment.
4. Validate supported static outcome profile and fixed safety invariants: unknown outcome requires stop/reconciliation; automatic retry is forbidden; automatic rollback is forbidden; no completion without a future receipt-verification boundary.
5. If immutable G2.4.17 evidence is supplied, reject `AMBIGUOUS` as terminal for automatic progress; do not read or mutate its ledger.
6. Produce only immutable outcome-policy assessment evidence.

No fallback profile, policy downgrade, policy synthesis, implicit retry interpretation, automatic reconciliation, automatic rollback, or authority conversion is permitted.

### 6.6 Fail-closed and outcome-unknown matrix

| Condition | Required disposition | State/effect rule |
|---|---|---|
| Exact attested G2.4.18 evidence plus exact supported policy | `OUTCOME_POLICY_ATTESTED` | Evidence only; no external request, receipt, network call, permit, claim, or durable state. |
| Missing/non-attested/expired/mismatched G2.4.18 evidence | `NOT_ATTESTED` | Do not recreate, re-attest, or override G2.4.18 evidence. |
| Policy digest/schema/timestamp/field set invalid | `NOT_ATTESTED` | Fail closed; no policy synthesis or fallback. |
| Contract ID/digest, contract assessment ID/digest, destination, operation, receipt schema, or idempotency profile differs | `NOT_ATTESTED` | Typed exact-binding finding; no request formation or execution inference. |
| Unsupported outcome profile or taxonomy | `UNSUPPORTED_OUTCOME_POLICY` | No compatibility mode or downgrade. |
| Policy permits automatic retry, automatic rollback, automatic release/publication/deployment, or completion without future verification | `NOT_ATTESTED` | Policy is unsafe by definition; no automatic progression. |
| Future receipt class is declared as outcome-unknown | No present execution outcome exists; declared policy must require stop | A future executor/verifier must stop and require separately authorized reconciliation; G2.4.19 itself cannot reconcile. |
| Supplied G2.4.17 `AMBIGUOUS` decision | `NOT_ATTESTED` | No clear, release, retry, read, claim, consume, reset, or reconcile effect. |
| Competing policies or competing contracts | Unsupported/deferred | Request supplies one policy and one G2.4.18 contract declaration; no selection, registry, precedence, or reconciliation authority exists. |
| Request to dispatch, verify receipt, retry, roll back, publish, release, deploy, or reconcile | No such public API | Capability absent; no external effect. |

## 7. Durable-state requirements

G2.4.19 should own **no durable mutable state**. There is no external attempt, receipt, or outcome to persist. A durable outcome ledger before an external event would falsely imply an outcome lifecycle and duplicate G2.4.17’s local pre-execution control role.

The only permitted outputs are immutable in-memory assessment evidence. A future executor must consult G2.4.17 at attempt time. A future receipt verifier/reconciliation owner, if separately approved, must define its own durable receipt/unknown-outcome state without changing G2.4.17 meaning.

## 8. EBS-034 proposal — Deterministic External Outcome-Semantics Policy Rehearsal

**EBS-034** should be a standalone deterministic benchmark using public immutable G2.4.15–G2.4.18 fixtures and supplied outcome-semantics policy evidence. It must not instantiate a destination client, make a provider/network call, create a sendable request, use a credential, create a G2.4.17 ledger, write audit evidence, or create durable state.

| Direct proof scenario | Required assertion |
|---|---|
| Exact READY → ELIGIBLE → AUTHORIZED → non-ambiguous control evidence → `CONTRACT_ATTESTED` contract evidence → exact policy | `OUTCOME_POLICY_ATTESTED`; all exact evidence IDs/digests and declared semantics are present in immutable references. |
| Equivalent independently reconstructed policy/request evidence | Same canonical request/policy/assessment digests; no hidden state. |
| One-field policy variation | Every non-target authoritative field is directly preserved; changed policy binding returns typed refusal and no progression. |
| Contract ID/digest, contract-assessment ID/digest, destination, operation profile, receipt schema, idempotency profile, outcome taxonomy variation | Exact typed binding refusal; no request, receipt, or durable state. |
| Missing/non-attested/expired G2.4.18 evidence | `NOT_ATTESTED`; no re-attestation or policy override. |
| Policy that permits automatic retry, rollback, release/publication/deployment, or unverified completion | Deterministic refusal; no automatic recovery semantics. |
| Outcome-unknown declaration | Attested only when it explicitly requires automatic stop and separate reconciliation; no reconcile API exists. |
| G2.4.17 `AMBIGUOUS` evidence | Deterministic refusal; no ledger operation, execution, permit, session, or request. |
| Strict canonical contracts | Frozen/slots objects; mutation refusal; no mutable public containers; UTC normalization; exact payload field set; self-digest rejection on tamper. |
| No durable state | Test-owned temporary root remains empty; source/API audit finds no store/cache/registry/global state owner. |
| Negative capability audit | No `execute`, `connect`, `request`, `send`, `upload`, `publish`, `deploy`, `promote`, `release`, `retry`, `rollback`, `reconcile`, `complete`, `finalize`, `create_session`, `issue_permit`, `claim`, `read`, `consume`, `reset`, `delete`, `clear`, `overwrite`, `force_claim`, `write`, or `mutate` capability. |

### Zero-effect semantics

G2.4.19 should use the same truthful classification adopted for the non-executable G2.4.18 boundary:

| Classification | Meaning for G2.4.19 |
|---|---|
| `DIRECT_STATE_PROOF` | Immutable supplied evidence, policy, request, result, and test-owned filesystem state are unchanged before/after pure assessment. |
| `CAPABILITY_ABSENT` | Provider, upload, network, credential, workspace, command, runtime, session, permit, transition execution, audit write, destination interaction, release, publication, deployment, and G2.4.17 ledger mutation/read have no reachable path. |
| `OBSERVED_ZERO_EFFECT` | Not applicable unless a future real reachable effect boundary exists. Local literal counters or unconnected sentinels are prohibited as proof. |

## 9. Negative-capability requirements

The public package and assessor must not expose any method or equivalent operation for execution, destination access, request construction, credential use, egress, receipt parsing, receipt verification, completion, release/publication/deployment state, retries, rollback, reconciliation, permits, sessions, ledger mutation/read, or audit writes.

Protected paths must remain unchanged and must not import G2.4.19: CLI; autonomous runtime; Chief; Coordinator; generic capability runtime; governed runtime; activation; approval; session; invocation; workspace custody; composition; governed execution lifecycle; G2.4.5 audit; G2.4.14 readiness; G2.4.15 promotion; G2.4.16 authorization; G2.4.17 control; G2.4.18 destination contract; legacy command execution and rollback paths.

## 10. Migration impact and explicit deferrals

G2.4.19 should be opt-in and consume public immutable evidence only. It must not migrate any existing caller or become part of a runtime path. Its introduction must not modify G2.4.14–G2.4.18 semantics.

The following remain explicitly deferred:

- trusted destination-contract issuer/root, signature verification, revocation, policy selection, and competing-contract selection;
- external request formation, payload construction, account selection, credentials, signing, transport, egress, connection, timeout, destination client, provider call, and executor;
- external receipt acquisition, receipt parsing, trusted receipt verification, destination-side query, completion fact, and release/publication/deployment state;
- reconciliation, retry, rollback, recovery, unpublish, compensating action, and ambiguity resolution;
- audit writing for an external outcome or any change to G2.4.5 ownership;
- CLI/autonomous migration, Chief/Coordinator changes, generic capability-runtime changes, workspace mutation, and legacy execution-path integration.

## 11. Risks and unresolved design questions

| Question | Why unresolved | Required future owner or decision |
|---|---|---|
| Who trusts a destination-contract issuer? | G2.4.18 validates structural identity only. | Separate trust-policy/root authority; do not repurpose G2.4.16 human transition authorization. |
| Who selects among multiple valid contract or outcome-policy declarations? | No registry, precedence, or selection authority exists. | Separate policy-selection design. |
| Which receipt issuer or query can establish external truth? | No operation, endpoint, client, or receipt exists. | Future receipt-verification boundary with explicit trust model. |
| When may a future unknown outcome be reconciled? | No external state, receipt verifier, or reconciliation authority exists. | Separate reconciliation authority after receipt semantics and external execution are designed. |
| Which credential/account/egress policy applies to a future request? | No secret, account, route, or transport owner exists. | Separate credential and egress custody boundary. |
| What constitutes a valid compensating action? | No destination-specific effect model exists. | Separate rollback/recovery design; never infer from local command rollback. |

## 12. Acceptance criteria for a future implementation

A future G2.4.19 implementation is acceptable only if it directly proves all of the following:

| Criterion | Required evidence |
|---|---|
| Isolated evidence-only package | Frozen/slots contracts, strict schemas, canonical SHA-256 self-validation, UTC normalization, no mutable public state, and no operational handles. |
| Exact chain binding | Exact G2.4.18 attested request/assessment/contract evidence plus required G2.4.17 ambiguity stop evidence are bound without recreating earlier semantics. |
| Safety semantics | Unknown outcome requires automatic stop and separate future reconciliation; automatic retry, rollback, release/publication/deployment, and unverified completion are rejected. |
| Fail closed | Missing, malformed, expired, unsupported, conflicting, or mismatched evidence/policy produces typed refusal and no fallback. |
| No durable outcome state | No store, cache, registry, global mutable state, audit write, receipt, completion, or external lifecycle state exists. |
| Capability absence | EBS-034 directly audits public APIs/imports/call paths; it does not fabricate observed counters where no effect boundary exists. |
| Scope isolation | No protected path changes/imports and no changes to G2.4.14–G2.4.18 ownership. |

## References

[1]: `./src/eag/governed_destination_contract/models.py` — G2.4.18 immutable destination-contract fields, declared request/receipt identifiers, and contract self-identity.
[2]: `./src/eag/governed_destination_contract/assessor.py` — G2.4.18 pure evidence assessment and transition-control ambiguity stop.
[3]: `./src/eag/governed_invocation/models.py` and `./src/eag/governed_session/gate.py` — existing controlled runtime invocation/session boundaries, not external transition authority.
[4]: `./src/eag/governed_audit/models.py` — immutable governed-execution audit projection and no-resume interruption rule.
[5]: `./tests/test_ebs_033_destination_contract.py` — current standalone deterministic evidence-only EBS conventions, including direct binding, immutability, capability absence, and no-fabricated-observability proof.
[6]: `./G2_4_18_RECON_AND_DESIGN.md` — published design record for destination-contract evidence and explicit execution/receipt/reconciliation deferrals.

## Completion markers

```text
G2.4.19_RECON=COMPLETE
G2.4.19_DESIGN=COMPLETE
G2.4.19_IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
BENCHMARK_CHANGES=0
FIXTURE_CHANGES=0
PRODUCTION_CHANGES=0

NETWORK_INVOCATIONS=0
PROVIDER_CALLS=0
UPLOAD_CALLS=0
CREDENTIAL_ACCESS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
G2.4.20=NOT_STARTED
WORKTREE=DIRTY_G2_4_19_DESIGN_DOCUMENT_ONLY
STOPPED_AFTER_RECON_AND_DESIGN=YES
```
