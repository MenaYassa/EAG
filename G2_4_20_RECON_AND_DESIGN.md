# G2.4.20 Reconnaissance and Design — Governed Destination-Contract Attestation-Policy Evidence

**Status:** Reconnaissance and design only.
**Published documentation baseline:** `70f87e429a7e2dde8b49e1e3c5a0fcde054a885e`.
**Latest published engineering milestone:** `v2.4.19-g2.4.19` → `429f1ecf4782b1ce8f925c58a517b547999fb325`.
**Authorized artifact:** This document only.

> **Recommendation:** The next safe boundary is **G2.4.20 — Governed Destination-Contract Attestation-Policy Evidence**. It should be an isolated, immutable, deterministic, non-executable validator of a supplied policy declaration that is exactly bound to one G2.4.18 destination-contract evidence chain and one G2.4.19 outcome-semantics policy assessment. It may classify whether declared issuer/reference metadata satisfies a supplied static policy. It must **not** claim that an issuer is genuine, that a contract is trusted external truth, or that any external transition is permissible.

This recommendation is deliberately **not** an executor, destination client, credential owner, transport or egress policy, request-envelope builder, signature verifier, receipt handler, reconciliation service, retry mechanism, rollback authority, release/publication/deployment state owner, or registry.

## 1. Executive finding

G2.4.14 through G2.4.19 establish an increasingly exact local evidence chain. They prove artifact readiness, logical promotion eligibility, bounded human authorization, local durable pre-execution control, structural destination-contract consistency, and safe future outcome semantics. The chain still lacks a governed vocabulary for deciding whether the **declared** G2.4.18 attestation issuer and reference are acceptable under a supplied policy. G2.4.18 checks the structural form of those declarations; it does not own a trust root, verify a signature, select among issuer declarations, query a source, or establish live destination truth.[1]

The safe next step is therefore to define a **policy evidence boundary for declared contract-attestation provenance before any verification or external action exists**. This mirrors the G2.4.19 sequencing principle: first bind safety-critical semantics to exact immutable evidence; only later, after distinct design approval, consider a verifier or other operational authority.

## 2. FACT — published authority chain through G2.4.19

| Milestone | Published tag | Authority it owns | What it explicitly does not own |
|---|---|---|---|
| G2.4.14 — Artifact Readiness | `v2.4.14-g2.4.14` | Immutable evidence that a supplied artifact snapshot meets readiness and hygiene requirements. | Destination acceptance, upload, release, or external effect. |
| G2.4.15 — Promotion Eligibility | `v2.4.15-g2.4.15` | Logical-destination eligibility evidence bound to readiness and lineage. | Endpoint selection, destination protocol, credentials, request, or receipt. |
| G2.4.16 — External Transition Authorization | `v2.4.16-g2.4.16` | Immutable human transition authorization evidence. | Permit, request, external attempt, receipt, retry, or recovery. |
| G2.4.17 — Transition Control Ledger | `v2.4.17-g2.4.17` | **Sole** durable, fail-closed pre-execution duplicate/conflict/ambiguity control ledger. | Destination-side idempotency, external completion, retry, reconciliation, or release. |
| G2.4.18 — Destination Contract Evidence | `v2.4.18-g2.4.18` | Immutable structural evidence binding a non-secret destination contract to the authorized chain and declared request/receipt/idempotency identifiers. | Trust root, issuer verification, endpoint, client, credentials, egress, receipt parsing, or live destination truth. |
| G2.4.19 — Outcome-Semantics Policy Evidence | `v2.4.19-g2.4.19` | Immutable policy evidence binding safe future outcome taxonomy and unknown-outcome stop semantics to exact G2.4.18 evidence. | Outcome, attempt, receipt, verification, completion, retry, rollback, reconciliation, publication, release, deployment, or external effect. |

The current chain is therefore:

```text
Artifact readiness evidence
        ↓
Logical-destination promotion eligibility evidence
        ↓
Human external-transition authorization evidence
        ↓
G2.4.17 durable pre-execution control decision
        ↓
G2.4.18 destination-contract evidence
        ↓
G2.4.19 outcome-semantics policy evidence
        ↓
[missing: governed policy for declared contract-attestation provenance]
```

G2.4.17 remains the only durable pre-execution control ledger. G2.4.18 remains destination-contract evidence only. G2.4.19 remains outcome-semantics policy evidence only. A positive attestation at any stage is local immutable evidence; it is not a destination-side fact and does not make an operation executable.

## 3. FACT — precise remaining semantic gap

`ExternalDestinationContractEvidence` contains `attestation_issuer_identity` and `attestation_reference`, but G2.4.18 accepts only their structural identifier shape and performs a fixed prefix-form check. Its public contract states that it neither asserts live destination truth nor exposes an endpoint, account, credential, request payload, release state, or external receipt. Its design record separately defers issuer trust roots, signature verification, revocation, and policy selection.[1] [2]

G2.4.19 correctly consumes exact G2.4.18 evidence but cannot turn declared issuer/reference metadata into trust. Its concern is future outcome classification: unknown outcomes must stop; automatic retry and rollback are forbidden; completion requires a future receipt-verification authority.[3]

Consequently, the remaining gap is not “send the artifact” or “verify a receipt.” It is the prior semantic question:

> “Does one supplied, immutable, non-secret policy declaration permit this exact contract’s **declared attestation identity and reference** to be used as a future verification input, while preserving the fact that no issuer authenticity or external destination truth has been established?”

This narrow question can be answered deterministically without an external source, a key, a network path, a client, a registry, or mutable state.

## 4. INFERENCE — boundaries enabled and still blocked

| Observation | Architectural inference | Consequence |
|---|---|---|
| The contract contains issuer/reference declarations but no trust root or verifier. | Structural validity is not provenance authenticity. | A later verifier must not rely on G2.4.18 attestation fields without separately governed policy and verification authority. |
| G2.4.19 binds safe unknown-outcome rules but never produces outcome evidence. | Future external safety semantics are defined before any receipt exists. | The same sequencing can safely define contract-attestation acceptance semantics before signature or source verification exists. |
| G2.4.17 owns durable local pre-execution control. | Provenance-policy evidence must not claim, read, consume, reset, or replace the ledger. | G2.4.20 must consume no ledger and introduce no durable state. |
| No governed external client, credential, transport, receipt, executor, or reconciliation package exists. | No operational transition is currently architecturally legitimate. | G2.4.20 must remain a library-only evidence boundary. |

## 5. Candidate next boundaries

| Candidate | Purpose | Architectural value | Primary risk | Decision |
|---|---|---|---|---|
| **A. Destination-contract attestation-policy evidence** | Bind a supplied static policy to the exact G2.4.18 contract declaration and G2.4.19 policy assessment; classify declared issuer/reference policy compliance. | Establishes the required semantics before a later trust verifier can exist. | Could be mislabeled as issuer authenticity or policy selection unless disposition names and exclusions are explicit. | **Recommended.** |
| B. Cryptographic contract-attestation verifier | Verify a signature or equivalent issuer proof. | Would eventually establish authenticity evidence. | Requires unresolved key/trust-root custody, signature formats, revocation, rotation, policy selection, and provenance-material input design. | Defer. |
| C. External request envelope | Bind a sendable request to current evidence. | Needed immediately before a future attempt. | Premature: there is no trusted contract source, credentials, account model, egress policy, transport, timeout owner, or executor. | Reject as next step. |
| D. Credential and egress custody | Define account, secret, and route control. | Needed before an external request. | Broad, sensitive authority before contract trust verification, request semantics, and an execution design. | Defer. |
| E. Receipt/verification boundary | Classify a destination response or query result. | Needed after a future attempt. | There is no external attempt, receipt payload, verifier trust model, or query authority. | Defer. |
| F. Reconciliation/retry/rollback boundary | Address an uncertain external effect. | Necessary after effects and receipt semantics exist. | No external state owner exists; automatic recovery would contradict G2.4.19 safety. | Defer. |
| G. Policy selection registry | Select among multiple policies or contracts. | Could support future scale. | Introduces precedence, registry/state, and conflict authority that the current chain deliberately does not own. | Defer. |

## 6. Recommended G2.4.20 boundary

### 6.1 Name and narrow purpose

**G2.4.20 — Governed Destination-Contract Attestation-Policy Evidence Boundary** should validate a supplied, immutable policy declaration against exactly one G2.4.18 contract-assessment chain and exactly one G2.4.19 outcome-policy assessment.

It should answer only:

> “Is the declared attestation issuer identity and reference on this exact G2.4.18 contract permitted by this exact immutable attestation-policy declaration, while preserving that the declaration has not been authenticated, queried, or externally verified?”

A positive disposition should be named **`ATTESTATION_POLICY_ATTESTED`**, not `CONTRACT_TRUSTED`, `ISSUER_VERIFIED`, `DESTINATION_VERIFIED`, `READY_TO_EXECUTE`, or any equivalent operational claim.

### 6.2 Authority ownership and boundary

| Concern | Owner after proposed G2.4.20 | Boundary |
|---|---|---|
| Attestation issuer/reference policy compliance | **G2.4.20 assessor** | Validate one supplied policy declaration against one exact G2.4.18 contract and one exact G2.4.19 assessment. |
| Artifact readiness | G2.4.14 | Unchanged. |
| Logical-destination eligibility | G2.4.15 | Unchanged. |
| Human transition authorization | G2.4.16 | Unchanged. |
| Durable duplicate/conflict/ambiguity control | G2.4.17 | Unchanged and remains sole ledger owner. G2.4.20 has no ledger collaborator. |
| Destination contract structural consistency | G2.4.18 | Unchanged. G2.4.20 must not recreate or re-attest the contract. |
| Future outcome safety semantics | G2.4.19 | Unchanged. G2.4.20 must not reinterpret receipt taxonomy, retry, rollback, completion, or reconciliation rules. |
| Contract issuer authenticity and revocation | No owner yet | Explicitly deferred to a later verifier/trust-root authority. |
| External operation, destination state, receipt, and reconciliation | No owner yet | Explicitly deferred. |

### 6.3 Proposed immutable contracts for a future implementation

All future G2.4.20 contracts must be frozen, slots-based, keyword-only, strictly typed, free of mutable public containers and operational handles, schema-versioned, UTC-normalized where time appears, canonically serialized, and SHA-256 self-validating.

| Contract | Canonically bound content | Explicit exclusions |
|---|---|---|
| `DestinationContractAttestationPolicyEvidence` | Policy self-identity; exact G2.4.18 contract ID/digest and contract-assessment ID/digest; exact G2.4.19 policy ID/digest and assessment ID/digest; destination identity; declared attestation issuer identity; declared attestation reference; one static attestation-policy profile; issuance/expiry; schema; policy digest. | Key, certificate, signature, endpoint, URL, credential, account, request payload, network handle, registry key, selector, verifier callable, receipt, completion state, or recovery command. |
| `AttestationPolicyAssessmentRequest` | Exact immutable G2.4.18 request/assessment, exact immutable G2.4.19 request/assessment, and one policy declaration. | G2.4.17 ledger, permit, session, runtime, executor, client, credential, store, cache, registry, audit writer, or callback. |
| `AttestationPolicyFinding` | Typed deterministic evidence reference and non-operational recommendation. | Signature result, issuer-verification result, destination response, secret, external state, or executable remediation. |
| `AttestationPolicyAssessment` | Assessment identity; destination and policy identities; immutable findings/references/recommendations; disposition; digest; timestamp. | Trust grant, external authorization, permit, claim, receipt, verification result, completion record, release/deployment state, or reconciliation authority. |
| `DestinationContractAttestationPolicyAssessor` | Pure validation of supplied immutable evidence and static policy profile. | Network, filesystem store, key resolution, signature verification, source query, ledger operation, request formation, credential use, runtime dispatch, retry, rollback, reconciliation, or audit write. |

The policy ID is **self-identity only**. There is no policy selection, precedence, conflict resolution, registry, or reconciliation authority. Multiple policy declarations are unsupported/deferred; a request contains exactly one supplied policy declaration.

### 6.4 Required validation order

1. Validate exact request types, immutable contract shape, schemas, timestamps, and self-digests.
2. Require supplied G2.4.18 assessment disposition `CONTRACT_ATTESTED`; otherwise fail closed without recreating or reassessing it.
3. Require supplied G2.4.19 assessment disposition `OUTCOME_POLICY_ATTESTED`; otherwise fail closed without reinterpreting outcome semantics.
4. Bind exact contract ID/digest, contract assessment ID/digest, destination identity, policy ID/digest, policy assessment ID/digest, declared issuer identity, and declared reference.
5. Require the one supported static attestation-policy profile and a non-expired policy.
6. Produce only immutable attestation-policy assessment evidence.

The assessor must not decide whether an issuer is genuine. It must not resolve a reference, authenticate a signing key, make a source query, or convert policy compliance into contract trust.

## 7. Fail-closed matrix for a future implementation

| Condition | Required disposition | State/effect rule |
|---|---|---|
| Exact `CONTRACT_ATTESTED` G2.4.18 evidence, exact `OUTCOME_POLICY_ATTESTED` G2.4.19 evidence, and exact supported attestation policy | `ATTESTATION_POLICY_ATTESTED` | Evidence only; no contract-trust claim, request, receipt, network call, permit, ledger operation, or durable state. |
| Missing, malformed, expired, non-attested, or mismatched G2.4.18/G2.4.19 evidence | `NOT_ATTESTED` | Do not recreate, re-attest, downgrade, or override upstream evidence. |
| Policy ID/digest/schema/timestamp/field set invalid | `NOT_ATTESTED` | Fail closed; no policy synthesis or fallback. |
| Contract ID/digest, contract assessment ID/digest, outcome policy ID/digest, outcome assessment ID/digest, destination, issuer identity, or reference differs | `NOT_ATTESTED` | Typed exact-binding finding; no source lookup or external verification. |
| Unsupported attestation-policy profile | `UNSUPPORTED_ATTESTATION_POLICY` | No compatibility mode or implicit broadening. |
| Competing policies, contracts, issuers, or references | Unsupported/deferred | No selection, precedence, registry, or reconciliation semantics. |
| Request to verify signature, resolve issuer, contact destination, form request, execute, receive/verify receipt, retry, roll back, reconcile, publish, release, or deploy | No public API | Capability absent; no external effect. |

## 8. Deterministic benchmark proposal — EBS-035

**EBS-035 — Deterministic Destination-Contract Attestation-Policy Rehearsal** should use public immutable G2.4.18 and G2.4.19 fixture evidence plus a supplied G2.4.20 policy declaration. It must not instantiate a destination client, source resolver, certificate/key store, network transport, provider, executor, ledger, session, permit, audit writer, or durable store.

| Direct proof scenario | Required assertion |
|---|---|
| Exact G2.4.18 `CONTRACT_ATTESTED` evidence + exact G2.4.19 `OUTCOME_POLICY_ATTESTED` evidence + exact static policy | `ATTESTATION_POLICY_ATTESTED`; immutable references contain exact contract, outcome-policy, issuer, and reference identities/digests. |
| Equivalent independently reconstructed evidence | Same canonical policy/request/assessment payloads and digests; no hidden state. |
| One-field authoritative mutation | The target field differs and every other authoritative field is directly preserved; real assessor emits the exact typed refusal with no progression. |
| Contract and outcome-policy upstream mismatch | Exact typed refusal; no upstream reassessment, request, receipt, or durable state. |
| Policy expiry/schema/timestamp/supplied-digest tamper | Strict parser or constructor refusal; no fallback and no progression. |
| Policy self-identity change | Distinct valid declaration/digest and normal attestation behavior; no selection, precedence, conflict, or reconciliation semantics. |
| Immutable evidence/result proof | Frozen/slots objects; no `__dict__`; mutation refusal; no mutable public containers; test-owned root unchanged. |
| Capability-absence proof | Public API/import/source/call-path audit demonstrates no external or durable operational path. |

## 9. B5/B6 truthful proof classification

The future G2.4.20 benchmark must classify proof accurately:

| Classification | Required meaning |
|---|---|
| `DIRECT_STATE_PROOF` | Supplied immutable evidence, policy, request, result, and test-owned filesystem state are preserved before and after pure assessment. |
| `CAPABILITY_ABSENT` | Executor, client, network, credential, key store, signature verifier, source resolver, receipt handler, session, permit, G2.4.17 ledger operation, audit writer, registry, retry, rollback, reconciliation, release, publication, and deployment have no reachable path. |
| `OBSERVED_ZERO_EFFECT` | **Not applicable.** No reachable effect boundary exists. Literal counters, fake zero-effect dictionaries, unconnected sentinels, hooks, observers, callbacks, instrumentation, or artificial seams are prohibited. |

## 10. Negative-capability requirements

A future G2.4.20 package and its public assessment output must not expose any literal or semantic equivalent of:

```text
execute, dispatch, send, request, connect, resolve, verify_signature,
load_key, credential, authenticate, upload, publish, release, deploy,
receipt, complete, finalize, retry, rollback, reconcile, claim, read,
consume, reset, delete, clear, overwrite, force_claim, create_session,
issue_permit, write, mutate
```

It must own no store, cache, registry, global mutable state, worker, executor, client, provider, transport, credential, secret, key, session, permit, receipt, audit writer, release state, or external destination collaborator.

Protected paths must remain unchanged and must not import G2.4.20: CLI; autonomous runtime; Chief; Coordinator; generic capability runtime; governed runtime; activation; approval; session; invocation; workspace custody; composition; governed execution lifecycle; governed audit; G2.4.14 readiness; G2.4.15 promotion; G2.4.16 authorization; G2.4.17 transition control; G2.4.18 destination contract; G2.4.19 outcome policy; and legacy command execution or rollback paths.

## 11. Explicit deferrals

The following are deliberately outside G2.4.20 and require separate design and authorization:

- trusted root/key/certificate custody, signature verification, issuer authentication, revocation, rotation, and provenance-material parsing;
- policy selection, precedence, registry, conflict resolution, and competing contract/issuer handling;
- external request formation, payload construction, account selection, credentials, signing, transport, egress, network connection, timeout, client, provider call, executor, and destination operation;
- receipt acquisition, receipt parsing, receipt authenticity, destination query, external outcome, completion fact, and release/publication/deployment state;
- reconciliation, retry, rollback, recovery, compensating action, unknown-outcome resolution, and durable external-outcome state;
- G2.4.17 ledger access or any durable local control operation;
- CLI/autonomous integration, Chief/Coordinator changes, generic capability-runtime changes, workspace mutation, and changes to G2.4.14–G2.4.19 ownership.

## 12. Acceptance criteria for a future implementation

A future G2.4.20 implementation is acceptable only if it directly proves all of the following.

| Criterion | Required evidence |
|---|---|
| Isolated policy-evidence package | Frozen/slots immutable contracts, strict schemas, canonical SHA-256 self-validation, UTC normalization, no mutable public state, and no operational handles. |
| Exact upstream binding | Exact supplied G2.4.18 request/assessment/contract and G2.4.19 request/assessment/policy evidence is bound without recreating upstream semantics. |
| Declared-provenance semantics only | Positive disposition proves only policy compliance of declared issuer/reference metadata; it does not claim contract trust, issuer authentication, signature verification, destination truth, or execution readiness. |
| Policy self-identity | ID-only change creates a distinct valid declaration/digest; no selection, precedence, conflict, registry, or reconciliation authority exists. |
| Fail closed | Missing, malformed, expired, unsupported, tampered, mismatched, or competing evidence/policy produces typed refusal without fallback. |
| G2.4.17/18/19 preservation | No ledger collaborator or operation; no contract reassessment; no outcome-policy reinterpretation; no changed public ownership. |
| No durable or operational authority | No store/cache/registry/global state, audit write, source/key resolution, client, receipt, outcome, completion, or external lifecycle state exists. |
| Capability absence | EBS-035 directly audits APIs/imports/call paths; it does not fabricate observed-zero-effect counters. |
| Scope isolation | No protected-path changes/imports and no changes to G2.4.14–G2.4.19 packages, tests, or semantics. |

## References

[1]: `./src/eag/governed_destination_contract/models.py` — G2.4.18 immutable contract declarations, including issuer/reference fields and explicit non-operational exclusions.

[2]: `./src/eag/governed_destination_contract/assessor.py` — G2.4.18 structural issuer/reference check and pure contract assessment behavior.

[3]: `./src/eag/governed_outcome_policy/models.py` and `./src/eag/governed_outcome_policy/assessor.py` — G2.4.19 immutable policy evidence and mandatory unknown-outcome safety semantics.

[4]: `./G2_4_19_RECON_AND_DESIGN.md` — G2.4.19 design record, including explicit deferral of contract issuer trust roots, signatures, revocation, and policy selection.

## Completion markers

```text
G2.4.20_RECON=COMPLETE
G2.4.20_DESIGN=COMPLETE
IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
FIXTURE_CHANGES=0
BENCHMARK_CHANGES=0
GIT_MUTATIONS=0

REAL_PROVIDER_CALLS=0
UPLOAD_CALLS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
WORKSPACE_MUTATIONS=0
COMMAND_EXECUTIONS=0
RUNTIME_CALLS=0
SESSION_CREATION=0
PERMIT_ISSUANCE=0
TRANSITION_EXECUTIONS=0

G2.4.21=NOT_STARTED
STOPPED_AFTER_RECON_AND_DESIGN=YES
```
