# G2.4.18 Reconnaissance and Design — Governed External Destination Contract Evidence

**Status:** Reconnaissance and design only.
**Published baseline:** `a8e7e44982e4b97045afd8a7f91fd5625d9d6a53` (`v2.4.17-g2.4.17`).
**Authorized artifact:** This document only.

> **Recommendation:** The narrowest safe next milestone is **G2.4.18 — Governed External Destination Contract Evidence Boundary**. It should be a library-only, immutable, deterministic validator of supplied, non-secret destination-contract evidence bound to an exact G2.4.16 authorized transition intent. It must not resolve a destination, access credentials, perform a network probe, create an external operation request, consume a G2.4.17 control claim, issue a permit, or infer that any external side effect is safe or completed.

The current system has reached a complete local pre-execution chain: artifact readiness, promotion eligibility, human transition authorization, and durable duplicate/conflict/ambiguity control. What is still absent is a governed **non-secret contract for the destination-facing protocol that a future executor would be required to obey**. The recommended boundary establishes evidence consistency for that future contract without introducing a destination client or treating attestation as live reachability.

## 1. FACT — repository-supported findings

| Area | Repository-supported fact | Consequence for a future executor |
|---|---|---|
| Artifact readiness | G2.4.14 accepts supplied immutable artifact snapshot, validation-receipt, and hygiene evidence; it produces `READY`, `NOT_READY`, or `UNSUPPORTED_PROFILE` only. Its validation receipts are evidence and never execute commands. [1] | A future executor can receive an exact artifact ID/fingerprint, but G2.4.14 neither owns a destination nor proves an external artifact was accepted. |
| Promotion eligibility | G2.4.15 binds the exact readiness assessment, artifact identity, declared lineage, promotion policy, and a logical destination identity. Supported destinations are non-secret identifiers such as `artifact-store-A`, `internal-registry`, and `pypi-production`; a URL, credential-like value, or client is excluded. [2] | There is already a narrow logical destination selection, but no destination-side protocol, endpoint, service identity, request schema, or receipt schema owner. |
| Human authorization | G2.4.16 validates a supplied explicit human decision bound to the exact G2.4.15 intent, artifact, logical destination, policy digests, execution/run identity, expiry, and authorization evidence. Its `AUTHORIZED` assessment and durable receipt are explicitly evidence-only. [3] | Human authorization is present and must not be duplicated by another execution-authorization or permit boundary. |
| Durable pre-execution control | G2.4.17 derives an authoritative control key from the exact authorized-transition identity, retains caller idempotency as complete binding evidence, and provides only durable `claim`/`read` operations. Its persisted states are `CLAIMED` and `AMBIGUOUS`; public outcomes include `DUPLICATE`, `CONFLICT`, and `NOT_CONTROLLABLE`. [4] | A later executor must consult G2.4.17 before an external attempt. A `CLAIMED` decision is neither permission nor an external receipt; `AMBIGUOUS` must remain a stop state. |
| Destination abstraction | No governed destination client, registry adapter, package publication interface, upload client, deployment adapter, external request model, or destination receipt/verification model is published. Repository uses of “registry” are internal strategy/benchmark/runtime registries, not external artifact destinations. [5] | There is no safe component that can contact a destination or represent destination acceptance. |
| Credential and egress custody | Project dependencies contain no dedicated registry or HTTP client integration, and the existing secret-related code is repository-context redaction rather than credential acquisition, storage, rotation, authorization, or egress control. [5] [6] | No existing component may be reused as destination credentials, a secret manager, or outbound network authority. |
| Generic execution and rollback | Legacy command and rollback facilities concern local subprocess/checkpoint execution. They do not model destination idempotency, registry publication, external receipt verification, unpublication, or recovery. [7] | They are protected legacy paths and must not be used as an artifact transition executor or recovery owner. |
| Audit ownership | G2.4.5 is an observer-only governed-execution audit boundary. It is not an external transition ledger, destination receipt store, or external reconciliation authority. [8] | G2.4.18 must not write audit records or create a parallel destination audit ledger. |

The repository therefore supports statements about **local evidence consistency**. It does not support statements that a destination is reachable, authenticated, healthy, authorized for a specific account, idempotent, or has accepted an artifact.

## 2. Current authority map

| Concern | Existing owner | Current state | G2.4.18 role |
|---|---|---|---|
| Artifact identity, snapshot, readiness, packaging, hygiene | G2.4.14 | Published evidence boundary | Consume only by reference; never revalidate, repair, or mutate artifact evidence. |
| Declared promotion lineage and logical destination | G2.4.15 | Published eligibility boundary | Consume the exact logical destination and policy binding; never reinterpret it as an endpoint or client configuration. |
| Human external-transition decision and expiry | G2.4.16 | Published authorization-evidence boundary | Consume exact authorization evidence; never approve, renew, reserve, or issue a permit. |
| Durable pre-execution duplicate/conflict/ambiguity state | G2.4.17 | Published claim/read ledger | Remain independent. G2.4.18 must not claim, read as authority, clear, consume, or reconcile control state. |
| Destination contract evidence consistency | **No owner exists** | Missing | **Recommended new G2.4.18 evidence-only owner.** |
| Destination endpoint/client/protocol execution | No owner exists | Missing | Explicitly deferred. |
| Credential custody and authentication | No owner exists | Missing | Explicitly deferred. |
| Egress authorization, allowlisting, and network timeout | No owner exists | Missing | Explicitly deferred. |
| External operation request dispatch | No owner exists | Missing | Explicitly deferred; no request object that can be sent may be introduced in G2.4.18. |
| Destination receipt and external verification | No owner exists | Missing | Explicitly deferred. |
| Reconciliation, retry, rollback, recovery | No owner exists for external transitions | Missing | Explicitly deferred. |
| Execution audit writing | G2.4.5 | Observer-only | Remains unchanged and is not invoked by G2.4.18. |

## 3. Missing capabilities before any external transition executor

The missing concerns are intentionally separated. They must not be compressed into a first executor implementation.

| Missing capability | Why it is not supplied today | Correct eventual owner | Why G2.4.18 cannot own it |
|---|---|---|---|
| Destination contract/profile | G2.4.15 has a logical identity only, without a bound operation or receipt contract. | G2.4.18 destination-contract evidence validator. | It may validate supplied evidence only; it cannot establish live destination truth. |
| External operation request | No immutable request schema describes what an executor may send to a particular destination. | A later bounded executor/request boundary. | A sendable request would invite execution authority and destination payload handling. |
| Credentials and secret custody | No secret broker, account binding, lease, rotation, or least-privilege design exists. | Separate credential-custody boundary. | Destination-contract evidence must contain no credential, token, endpoint authentication, or secret reference. |
| Egress and client authority | No allowlist, transport policy, timeout owner, connection factory, or client abstraction exists. | Separate egress/client boundary. | An evidence validator must not import network libraries, create clients, or test reachability. |
| Destination-side idempotency | G2.4.17 owns local durable control, not destination deduplication semantics. | Future executor plus destination protocol/verification owner. | G2.4.18 may validate a declared destination idempotency profile, but cannot verify or invoke it. |
| External receipt and verification | No receipt schema, verifier, destination query, or trusted issuer exists. | Future post-execution receipt/verification boundary. | G2.4.18 cannot synthesize a receipt or infer success from a declaration. |
| Timeout, retry, ambiguous outcomes | No outbound attempt exists, so no observed timeout or destination outcome exists. | Future executor/reconciliation design. | G2.4.18 must not define automatic retry or reinterpret G2.4.17 `AMBIGUOUS`. |
| Rollback/recovery | Existing rollback is not destination-specific. | Future destination-specific recovery owner. | No unpublish/reversal action, credential, or external state model exists. |
| Release/publication state | No external lifecycle state is modeled. | Future receipt/verification/reconciliation owner. | G2.4.18 must not add release state, a publication record, or a completion field. |

## 4. Candidate next milestones

| Candidate | Purpose | Architectural value | Primary risk | Decision |
|---|---|---|---|---|
| **A. Governed External Destination Contract Evidence Boundary** | Validate supplied non-secret destination-contract evidence against exact G2.4.15/G2.4.16 identity and policy bindings. | Establishes the first bounded, immutable description of what destination-facing profile a future executor must obey. | Could be misread as liveness, permission, or a client configuration unless contracts explicitly exclude those capabilities. | **Recommended.** |
| B. External transition execution-authorization / permit boundary | Issue a pre-execution permit after G2.4.16/G2.4.17. | Appears to simplify future orchestration. | Duplicates G2.4.16 human authorization and turns G2.4.17 `CLAIMED` into an unsafe permission proxy. | Reject. |
| C. Sendable external-transition request boundary | Define one executor input and later dispatch contract. | Eventually necessary before destination invocation. | Premature without destination contract, credential, egress, receipt, timeout, and reconciliation design. | Defer. |
| D. External transition receipt / verification boundary | Define destination outcome evidence. | Eventually required to close external outcomes. | No external operation or trustworthy receipt issuer exists; a synthetic receipt would overclaim success. | Defer. |
| E. Credential and egress custody | Define secret/transport control first. | Necessary before an executor. | High-risk authority with no bounded destination protocol or account model; would be overly broad. | Defer until destination contract evidence exists. |
| F. Destination client or executor | Contact a registry, package service, or deployment target. | Could perform the desired side effect. | Combines irreversible change, credentials, egress, idempotency, timeout, receipts, verification, and recovery without owners. | Reject. |
| G. Reconciliation / rollback | Address uncertain/failed external outcomes. | Eventually required after external execution. | No destination effect, receipt, or compensating operation exists to reconcile. | Defer. |

## 5. Recommended G2.4.18 — Governed External Destination Contract Evidence Boundary

### 5.1 Narrow purpose

G2.4.18 should answer only the following question:

> “Is the supplied immutable, non-secret destination-contract evidence structurally valid and exactly bound to the declared logical destination, G2.4.15 eligible transition, and G2.4.16 authorized transition intent, without implying that the destination is reachable, authenticated, willing to accept the artifact, or that an external transition may execute?”

This is an **evidence-consistency** boundary, not a live destination attestation. The word “contract” means a deterministic statement of the profile a future executor must later enforce; it does not mean a network connection, a production account, or a guarantee of remote behavior.

### 5.2 Why this boundary now

G2.4.15 validates a logical destination and G2.4.16 binds human authorization to that destination. G2.4.17 then prevents a future executor from treating the same authorized transition as indefinitely fresh. What remains undefined is the non-secret contract linking that logical destination to the future operation class, expected request/receipt schema identifiers, and declared destination idempotency semantics. Without this boundary, a future executor would have to invent those consequential destination semantics at execution time.

The recommended boundary is smaller and safer than a client, credential, egress, request, receipt, or permit system. It is independently testable from supplied fixtures, requires no network or secret, and does not convert any upstream evidence into execution authority.

### 5.3 Why not the alternatives now

An execution permit would repeat G2.4.16’s human decision and dangerously encourage treating G2.4.17 `CLAIMED` as executable. A sendable request contract is premature because no component owns credentials, egress, timeouts, payload construction, destination protocol, or observed outcomes. A receipt boundary is premature because no source can truthfully assert an external outcome. Credential/egress custody is necessary later but cannot be scoped safely until a non-secret destination contract says exactly which destination and operation it serves.

## 6. Proposed contract shape

All proposed contracts are **frozen, slots-based, immutable, canonicalizable, self-validating, UTC-normalized where time is present, and free of mutable metadata or operational handles**. Names are design proposals only; no source is authorized by this document.

| Proposed contract | Required responsibility and exact content | Explicitly excluded |
|---|---|---|
| `ExternalDestinationContractEvidence` | Immutable `destination_contract_id`; exact logical `destination_identity`; `transition_profile`; `operation_profile` as a non-executable declared operation class; `external_request_schema_id`; `external_receipt_schema_id`; `destination_idempotency_profile`; `destination_policy_digest`; attestation issuer/reference identity; issued/expiry timestamps; canonical `contract_digest`; schema version. | URL, hostname, IP, endpoint, port, account, tenant, credential, token, secret reference, authorization header, client instance, callable, transport configuration, retry count, payload bytes, artifact path, workspace handle, release state, or receipt of external success. |
| `DestinationContractAssessmentRequest` | Supplied exact G2.4.15 promotion eligibility request/assessment references, G2.4.16 transition intent/authorization receipt/assessment references, and one supplied `ExternalDestinationContractEvidence`. It validates only binding consistency. | G2.4.17 ledger object, control claim consumption, permit, session, runtime, executor, destination client, or network probe. |
| `DestinationContractFinding` | Typed, canonical, non-sensitive refusal/evidence reference. | Provider text, destination response body, secret material, dynamic client diagnostics, or operational remediation action. |
| `DestinationContractAssessment` | Immutable assessment ID; destination identity; disposition such as `CONTRACT_ATTESTED`, `NOT_ATTESTED`, or `UNSUPPORTED_DESTINATION_CONTRACT`; exact evidence references; typed findings; recommendations; timestamp; canonical digest. | Permit, reservation, `execute`, `send`, `connect`, release, destination receipt, publication state, reconciliation authority, or a statement that an external operation occurred. |
| `DestinationContractAssessor` | Pure/read-only validation of supplied published evidence and the supplied contract declaration. | Any durable claim/read/write beyond in-memory validation of supplied objects, credential access, networking, destination lookup, runtime dispatch, audit writing, or filesystem mutation. |

The `destination_contract_id` is the **canonical self-identity of the supplied declaration**. It is included in that declaration’s canonical representation and `contract_digest`; changing only the ID creates a distinct self-validating declaration. G2.4.15–G2.4.17 deliberately do not select, authorize, or control this identity, so G2.4.18 must not invent an expected contract ID or reject an otherwise exact declaration solely because its self-identity differs.

The `destination_idempotency_profile` is a **declared required capability profile** for a future executor to enforce and later verify. It is not proof that the destination currently implements idempotency and does not replace the durable local G2.4.17 control key.

The `external_request_schema_id` and `external_receipt_schema_id` are **identifiers only**. They prevent a future executor from choosing an unbound schema ad hoc; they do not introduce a sendable request, a receipt parser, or an external verification mechanism in G2.4.18.

## 7. Authority boundary

| G2.4.18 may do | G2.4.18 must not do |
|---|---|
| Validate immutable supplied destination-contract evidence. | Resolve, connect to, probe, or attest a live destination. |
| Compare exact G2.4.15/G2.4.16 identity, destination, policy, artifact, and profile bindings. | Issue approval, authorization, permit, reservation, session, or runtime-start authority. |
| Validate contract schema, canonical digest, issuer/reference shape, expiry, operation-profile support, and declared idempotency-profile compatibility. | Read, claim, consume, reset, mutate, clear, or reconcile the G2.4.17 ledger. |
| Return immutable `CONTRACT_ATTESTED`, refusal, or unsupported-profile evidence. | Treat `CONTRACT_ATTESTED` or G2.4.17 `CLAIMED` as permission to execute. |
| Bind future request/receipt schema **identifiers** to the destination contract. | Construct a request payload, create a destination client, send data, receive a response, or issue a receipt. |
| Preserve non-secret logical-destination semantics. | Accept endpoint URLs, authentication details, credentials, secrets, payload bytes, environment handles, or workspace paths. |

The future external executor, if separately authorized, must require all of the following without changing their ownership:

```text
G2.4.14 READY artifact evidence
        + G2.4.15 ELIGIBLE promotion evidence
        + G2.4.16 AUTHORIZED transition evidence
        + G2.4.17 non-AMBIGUOUS durable control state
        + G2.4.18 valid destination-contract evidence
        + [future credential/egress and executor authority]
        → at most one controlled external attempt
```

This sequence does not grant any current component a new right to execute. In particular, G2.4.17 `CLAIMED` remains only durable pre-execution control evidence and cannot be converted into a session, permit, release, upload receipt, destination acceptance, or completion fact.

## 8. Failure and fail-closed matrix

| Condition | G2.4.18 required assessment result | State/effect rule |
|---|---|---|
| Exact eligible, authorized, non-expired supplied evidence plus an exact supported destination contract | `CONTRACT_ATTESTED` | Evidence only; no permit, control-ledger claim, request, network call, or external state change. |
| Destination contract missing, malformed, non-canonical, invalid digest, invalid schema, or unexpected field | `NOT_ATTESTED` | Fail closed; do not synthesize a contract or use a fallback. |
| Contract destination differs from G2.4.15/G2.4.16 logical destination | `NOT_ATTESTED` with destination-binding finding | No external operation inference; no destination selection or conversion. |
| Contract artifact, promotion policy, authorization policy, intent, assessment, execution, or run binding differs | `NOT_ATTESTED` with typed binding finding | No override, merge, or normalization of conflicting evidence. |
| Authorization missing, denied, expired, corrupt, non-`AUTHORIZED`, or mismatched | `NOT_ATTESTED` | G2.4.18 does not re-authorize or extend expiry. |
| G2.4.15 evidence missing, non-eligible, corrupt, or mismatched | `NOT_ATTESTED` | G2.4.18 does not recreate readiness or eligibility evidence. |
| Unsupported operation/request/receipt/idempotency profile | `UNSUPPORTED_DESTINATION_CONTRACT` | No implicit compatibility mode or profile downgrade. |
| Equivalent supplied contract declaration | Exact same deterministic assessment only | G2.4.18 owns no durable claim and must not create a second ledger. |
| Competing contract declarations for one exact transition | Unsupported/deferred scenario | The request supplies exactly one declaration; no contract-selection, candidate-set, registry, reconciliation, or expected-ID authority exists. |
| Destination unavailable, timeout, or unreachable | No liveness conclusion is available | G2.4.18 performs no network observation and must not call a destination “available.” |
| G2.4.17 `AMBIGUOUS`, conflicting, or unavailable control state | No control-state mutation or reinterpretation | G2.4.18 must not clear, release, retry, or reconcile it. A future executor remains responsible for respecting G2.4.17 before any attempt. |
| Missing/untrusted attestation issuer or unbounded issuer-reference semantics | `NOT_ATTESTED` or unsupported profile | The boundary must not invent a trust root or accept self-asserted destination authority as live proof. |
| Request for upload, publish, deploy, release, retry, rollback, reconciliation, receipt, or verification | No such G2.4.18 API | Zero external effect. |

## 9. EBS-033 proposal — Deterministic Destination Contract Evidence Rehearsal

**EBS-033** should be an isolated deterministic benchmark using only prebuilt G2.4.14–G2.4.17 fixture evidence plus supplied immutable destination-contract declarations. It must not import or call a client, runtime, CLI, generic capability, provider, audit writer, credential store, or network library.

| Scenario | Required direct assertion |
|---|---|
| Exact READY → ELIGIBLE → AUTHORIZED chain plus exact valid destination contract evidence | `CONTRACT_ATTESTED`; exact destination identity, artifact fingerprint, promotion/authorization policy digests, intent ID, contract ID/digest, operation profile, and request/receipt schema identifiers appear in immutable evidence references. |
| Equivalent independently constructed contract evidence | Deterministically equivalent assessment/digest; no durable claim or hidden state. |
| Altered destination identity only | `NOT_ATTESTED`; typed destination-binding finding; no external request or control-ledger mutation. |
| Altered artifact fingerprint, promotion policy, authorization policy, transition intent, assessment ID/digest, execution ID, or run ID | `NOT_ATTESTED`; exact binding refusal; no state progression. |
| Missing, denied, expired, or altered G2.4.16 authorization evidence | `NOT_ATTESTED`; no reauthorization or extension. |
| Missing/non-eligible/altered G2.4.15 evidence | `NOT_ATTESTED`; no eligibility recreation. |
| Invalid/unsupported destination contract profile, schema, digest, request schema ID, receipt schema ID, or idempotency profile | Deterministic typed refusal; no compatibility fallback. |
| Expired destination contract evidence | `NOT_ATTESTED`; no live refresh or destination probe. |
| Contract declaration self-identity | Equivalent declarations yield identical canonical evidence/digest; an ID-only difference yields a distinct self-validating declaration/digest whose supplied identity is preserved in assessment evidence. Competing-declaration selection is deferred because no authority owns it. |
| Supplied G2.4.17 `AMBIGUOUS` evidence | No clear/retry/release/consume effect and no inference that execution is now safe. |
| Public negative-capability audit | No `execute`, `connect`, `request`, `send`, `upload`, `publish`, `deploy`, `release`, `retry`, `rollback`, `reconcile`, `complete`, `create_session`, `issue_permit`, `claim`, `consume`, `reset`, `delete`, or audit-write capability. |
| Side-effect audit | Provider, upload, network, credential, workspace, command, runtime, session, permit, transition-execution, audit-writer, destination-interaction, release, publication, and deployment counters are all zero. |

## 10. Side-effect invariants

G2.4.18 must have the following deterministic zero-effect requirements in unit tests and EBS-033:

```text
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
AUDIT_WRITER_CALLS=0
DESTINATION_INTERACTIONS=0
RELEASE_CALLS=0
PUBLICATION_CALLS=0
DEPLOYMENT_CALLS=0
CONTROL_LEDGER_MUTATIONS=0
```

No filesystem store, mutable cache, process-local fallback, audit append, or durable destination state is justified for this proposed evidence-consistency boundary.

## 11. Explicit deferrals

G2.4.18 must not implement any of the following:

- an external transition executor, destination client, registry adapter, package upload, publication, release, deployment, or destination probe;
- URLs, endpoints, hostnames, ports, headers, transport settings, payload bytes, request dispatch, response handling, or timeout execution;
- credential acquisition, storage, secret references, account/tenant selection, authentication, signing, rotation, or revocation;
- egress allowlists, network gateways, proxy configuration, socket/HTTP calls, or provider calls;
- a second human approval, transition authorization, permit, session, or invocation authority;
- a second idempotency ledger, any G2.4.17 claim/consume/reset/release/reconcile API, or a reinterpretation of `CLAIMED`/`AMBIGUOUS`;
- external receipt creation, destination verification, completion state, release state, reconciliation, automatic retry, rollback, recovery, unpublication, or deploy reversal;
- audit writes, workspace mutation, artifact mutation, repository mutation, CLI exposure, autonomous migration, Chief/Coordinator changes, capability-runtime integration, or runtime composition;
- changes to G2.4.14, G2.4.15, G2.4.16, or G2.4.17 ownership or semantics.

## 12. Migration and integration impact

G2.4.18 should add one isolated evidence-only package in a future, separately authorized implementation. It must consume public types only and remain opt-in. It must not be imported by the following protected paths:

| Protected path | Required status |
|---|---|
| CLI, autonomous runtime, Chief, Coordinator, generic capability runtime | Untouched; no import or behavioral migration. |
| Governed runtime, activation, approval, session, invocation, custody, composition, audit, execution state machine | Untouched; no new chaining, permit, session, invocation, or audit relationship. |
| G2.4.14 readiness, G2.4.15 promotion, G2.4.16 authorization, G2.4.17 control | Untouched; their public evidence may be consumed only by a future G2.4.18 assessor. |
| Legacy command execution, rollback, repository/workspace paths | Untouched; no reuse for a destination action or recovery operation. |

A later sequence remains explicitly staged: destination-contract evidence first; then separately designed credential/egress custody; then a bounded executor with one outbound attempt and mandatory G2.4.17 consultation; then destination receipt/verification; then separately designed reconciliation/recovery. No stage may be collapsed without new reconnaissance and authorization.

## 13. Acceptance criteria for a future implementation

A future G2.4.18 implementation is acceptable only if all of the following are directly proven.

| Criterion | Required evidence |
|---|---|
| Isolated evidence-only package | Public frozen/slots contracts, canonical SHA-256 digests, UTC normalization, strict schemas, and no operational handles. |
| Exact upstream binding | Every accepted assessment binds exact G2.4.15 logical destination and eligibility evidence plus exact G2.4.16 intent, authorization receipt, assessment, artifact, policy, execution/run, and expiry evidence. |
| Destination-contract limits | Contract accepts only non-secret logical identity and declared schema/profile identifiers; endpoint, credential, client, payload, and transport material are rejected. |
| Fail closed | Missing, malformed, expired, unsupported, mismatched, or untrusted contract evidence produces deterministic refusal with typed findings and no fallback. Contract selection among competing declarations is explicitly deferred because no authority owns it. |
| G2.4.17 preservation | No control claim/read/consume/reset/release/reconcile/write occurs; `CLAIMED` is never represented as a permit and `AMBIGUOUS` is never cleared. |
| No operational authority | EBS-033 and public capability audit prove zero side effects and absence of execution, connection, request, credential, session, permit, release, or reconciliation APIs. |
| Scope isolation | No protected path changes or imports; G2.4.14–G2.4.17 semantics and tests remain unchanged. |

## 14. Open questions

1. **Trust source:** What separate governance system, signature model, or policy store will establish that a supplied destination-contract declaration has a trusted issuer? The repository has no trust-root, signature-verification, or revocation authority today.
2. **Contract freshness:** What expiry period and revocation semantics are appropriate for destination-contract evidence without creating a live destination probe or mutable store?
3. **Operation taxonomy:** Which exact artifact transition classes should exist before any client is designed, and how should they relate to the existing G2.4.16 transition profile without broadening it?
4. **External idempotency semantics:** Which destination classes can honor an idempotency key, how should a future executor transmit it, and what verifier can prove that the destination honored it?
5. **Credential and egress ownership:** How will a later boundary bind an account, credential lease, allowlisted route, destination contract, and executor without exposing secrets in evidence or logs?
6. **Receipt trust and verification:** What minimal external receipt schema and verifier are required to distinguish accepted, rejected-before-side-effect, timed-out, and unknown outcomes?
7. **Ambiguity and reconciliation:** Which separately owned authority may inspect a destination after a lost response, and which conditions, if any, could move an external transition out of an ambiguous outcome?
8. **Recovery:** Which destination-specific compensating actions are valid, and how must a later recovery boundary prevent an unpublish/rollback from becoming an unconstrained second executor?

## References

[1]: ./src/eag/governed_artifact_readiness/models.py "G2.4.14 immutable artifact readiness contracts"
[2]: ./src/eag/governed_promotion/models.py "G2.4.15 promotion intent, logical destination, and eligibility contracts"
[3]: ./src/eag/governed_transition_authorization/models.py "G2.4.16 external transition authorization evidence"
[4]: ./src/eag/governed_transition_control/models.py "G2.4.17 transition-control request and immutable decision contracts"
[5]: ./pyproject.toml "Project dependencies and no external destination client integration"
[6]: ./src/eag/context/sensitivity.py "Repository-context redaction, not credential custody"
[7]: ./src/eag/execution/executor.py "Legacy local command execution"
[8]: ./src/eag/governed_audit/recorder.py "Observer-only governed execution audit"

## Completion markers

```text
G2.4.18_RECON=COMPLETE
G2.4.18_DESIGN=COMPLETE
IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
BENCHMARK_CHANGES=0

REAL_PROVIDER_CALLS=0
UPLOAD_CALLS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
WORKTREE=DIRTY_G2_4_18_DESIGN_DOCUMENT_ONLY
STOPPED_AFTER_RECON_AND_DESIGN=YES
```
