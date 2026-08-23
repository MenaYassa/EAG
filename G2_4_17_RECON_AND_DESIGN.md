# G2.4.17 Reconnaissance and Design — Governed External Transition Control Ledger

**Status:** Analysis and design only.
**Baseline:** `d5f4acf512543e3b2286b066b4a10cf587b88a6f` (`v2.4.16-g2.4.16`).
**Authorized deliverable:** This document only.

## Executive disposition

> **Recommendation:** The safest next milestone is **G2.4.17 — Governed External Transition Control Ledger**. It should be a library-only, immutable, durable control-state boundary that binds one exact G2.4.16 `AUTHORIZED` assessment to a transition-control key and records only pre-execution state: `UNCLAIMED`, `CLAIMED`, or `AMBIGUOUS`. It must not contact a destination, access credentials, execute a transition, issue a permit, or create a release receipt.

The existing architecture has reached **evidence**, **eligibility**, and **human authorization**, but it has no durable transition-wide idempotency or ambiguous-outcome control plane. An executor would therefore have no authoritative state to consult before attempting an irreversible action, no way to distinguish a fresh attempt from a duplicated request, and no durable record that an outcome is unknown. A destination client, credential boundary, egress control, external receipt, verification, reconciliation, and recovery authority are all still absent.

The recommended ledger is deliberately **not an executor**. It is a prerequisite state owner for a future separately authorized execution boundary. Its sole value is preventing a future executor from treating every eligible and authorized request as new.

## Current chain and remaining gap

```text
G2.4.14 artifact readiness evidence
        ↓
G2.4.15 promotion eligibility evidence
        ↓
G2.4.16 durable human transition-authorization evidence
        ↓
G2.4.17 proposed durable transition-control ledger
        ↓
[future separately authorized destination executor]
        ↓
[future destination receipt / verification / reconciliation]
```

The missing element is **not approval**. G2.4.16 binds an explicit human decision to the exact evidence chain and stores that immutable decision without making it executable. The missing element is **durable pre-execution transition control**: an independently checkable state that determines whether an exact external transition is fresh, already claimed, or unsafe to retry because the outcome is unknown.

## Repository-grounded facts

| Area | Fact from published contracts |
|---|---|
| Artifact identity | G2.4.14 evaluates immutable artifact identity, snapshot evidence, and fingerprint-bound readiness evidence. It does not produce a destination interaction. |
| Promotion eligibility | G2.4.15 validates `READY` G2.4.14 evidence, declared lineage, a logical destination identity, and a promotion policy digest. Its only supported destination values are logical non-secret identifiers; it has no URL, client, or connection. |
| Human authorization | G2.4.16 validates exact G2.4.15 `ELIGIBLE` evidence and writes a durable immutable authorization receipt. `AUTHORIZED` is explicitly evidence-only, not a permit, reservation, upload authorization, or transition result. |
| Existing durable state | The G2.4.16 store atomically `claim`s and `read`s immutable authorization receipts keyed by authorization identity. Its claim disposition is `CLAIMED`, `DUPLICATE`, or `CONFLICT`; it does not own destination-attempt state or outcomes. |
| Idempotency input | G2.4.16 transition intent includes an `idempotency_key`, but the published authorization store never claims or queries that key. No transition-wide key-to-state mapping exists. |
| Destination execution | No governed registry abstraction, package publishing interface, upload client, deployment abstraction, destination verifier, transition executor, or external receipt model is published. |
| Credential and egress custody | No governed credential/secret custody, authentication, egress allowlist, HTTP/socket boundary, or destination-connection policy is published. |
| Existing recovery | Repository rollback support is unrelated to an external artifact transition. There is no external transition rollback, reconciliation, or destination recovery owner. |
| Governance and audit | G2.4.9 remains session-oriented approval. G2.4.16 is distinct external-transition human authorization. G2.4.5 audit remains an observer-only execution audit and is not a second transition ledger. |
| Control-path isolation | G2.4.13 pre-session readiness, G2.4.7.1 invocation, G2.4.4 runtime, CLI, autonomous runtime, Chief, Coordinator, and capability runtime do not consume the G2.4.14–G2.4.16 artifact-transition evidence path. |

## Architectural inferences

The evidence chain is adequate to state: *this exact artifact was structurally ready, was eligible for a logical destination under a declared policy, and received a valid human decision*. It is not adequate to state: *an external transition may now be attempted safely*.

A future caller could present the same `AUTHORIZED` assessment repeatedly. The G2.4.16 authorization receipt itself is durably no-overwrite, but its identity is not a transition-control state, and its immutable claim does not decide whether an external side effect has begun, completed, failed before contact, or has an unknown outcome. A future executor that simply consumes the existing evidence would risk duplicate publication following process failure or lost response.

Destination identity remains intentionally logical. Before any client exists, EAG needs a pre-execution policy that makes the future executor consult one durable control state. This is safer than introducing a registry client, credentials, or egress configuration first, because none of those additions would resolve duplicate and ambiguous-outcome behavior.

## Candidate comparison

| Candidate | Architectural value | Why not the next milestone |
|---|---|---|
| **Artifact transition executor** | Could contact and alter a destination. | Unsafe: no destination configuration/attestation, credential custody, egress policy, idempotency state, result receipt, verification, reconciliation, or rollback model exists. |
| **External destination attestation** | Could describe a logical destination profile. | Necessary later, but without a durable transition-control key it does not prevent duplicate or ambiguous external effects. |
| **Release approval boundary** | Adds human governance. | Already addressed by G2.4.16 external-transition authorization. Repeating it would create a second approval authority. |
| **Transition receipt/evidence boundary** | Could represent successful destination outcomes. | Premature: no external operation exists from which a trustworthy receipt could be formed, and no verification owner exists. |
| **Provenance strengthening** | Could improve lineage quality. | Valuable but does not control duplicate attempts or unknown results at the irreversible boundary. |
| **Rollback/recovery boundary** | Could define recovery of a failed external change. | Premature without a destination model, transition receipt, and reconciliation semantics. |
| **Governed External Transition Control Ledger** | Establishes durable idempotency and an ambiguous-outcome stop state before any external effect. | **Recommended.** It is executable-state preparation only and can be validated without a destination client, credential, or network. |

## Recommended future milestone

### G2.4.17 — Governed External Transition Control Ledger

### Narrow purpose

Create one library-only owner of durable transition-control state for a future external executor. It binds an exact G2.4.16 `AUTHORIZED` assessment and exact `ExternalTransitionIntentEvidence` to an idempotency key and an immutable control record. It returns only evidence/control decisions; it must not itself cause an external effect.

### Ownership and boundary table

| Concern | Owner after G2.4.17 | Explicit non-owner |
|---|---|---|
| Artifact structure/readiness | G2.4.14 | G2.4.17 |
| Promotion eligibility and logical destination policy | G2.4.15 | G2.4.17 |
| Human external-transition decision | G2.4.16 | G2.4.17 |
| Durable pre-execution transition key/state | **G2.4.17** | G2.4.14–G2.4.16, future executor |
| Session approval | G2.4.9 | G2.4.17 |
| Session readiness | G2.4.13 | G2.4.17 |
| Invocation and runtime execution | G2.4.7.1 / G2.4.4 | G2.4.17 |
| Destination client, credential, and egress | No owner yet | G2.4.17 |
| External outcome receipt / verification / reconciliation | No owner yet | G2.4.17 |
| Audit writing | G2.4.5 | G2.4.17 |

### Proposed immutable contracts

| Contract | Required contents | Excluded contents |
|---|---|---|
| `ExternalTransitionControlRequest` | Control request ID; exact authorization assessment ID/digest; authorization ID/binding digest; transition intent ID; artifact ID/fingerprint; logical destination identity; promotion and authorization policy digests; canonical idempotency key; transition profile. | URL, endpoint, credential, secret, token, client, executable callback, workspace path, command, payload bytes. |
| `TransitionControlRecord` | Immutable control ID; request identity/digest; idempotency-key digest; control state; timestamp; schema version; canonical digest. | Upload response, external receipt, credential, retry count, mutable state, rollback action. |
| `TransitionControlDecision` | `CLAIMED`, `DUPLICATE`, `CONFLICT`, `AMBIGUOUS`, `NOT_CONTROLLABLE`, or `UNSUPPORTED_PROFILE`; typed findings; evidence references; canonical digest. | Permit, session, executor handle, release command, network result. |
| `DurableTransitionControlStore` | Atomic immutable `claim(request)` and validated `read(idempotency_key)` operations only. | Update, delete, reset, release, consume, retry, execute, complete, publish, reconcile, rollback. |

A control record should initially permit only two persisted states: **`CLAIMED`** and **`AMBIGUOUS`**. `AMBIGUOUS` must be append-only and terminal for automatic progression. It is reserved for a future executor to report that an external effect may have occurred but cannot be verified. G2.4.17 itself cannot create an ambiguous result from network behavior because it has no network behavior.

### Validation ordering

```text
1. Validate contract shape and supported profile.
2. Validate canonical request digest and idempotency-key form.
3. Validate exact G2.4.16 AUTHORIZED assessment and authorization receipt binding.
4. Validate exact G2.4.15 eligibility references already bound by G2.4.16.
5. Validate logical destination identity only; do not resolve or contact it.
6. Atomically claim the idempotency-key digest in the durable control store.
7. Return immutable control evidence only.
```

No future caller may receive a `CLAIMED` control decision when the key maps to a different binding. A same-binding repeat produces `DUPLICATE`, not a second claim. A key mapped to a different artifact, destination, policy, authorization, or intent produces `CONFLICT`. An existing `AMBIGUOUS` record produces `AMBIGUOUS` and must not enable automated retry.

### Durable-state requirements

The store must be injected, atomic, durable, no-overwrite, process-safe, fail-closed, and free of process-local fallback. It should use a separate control root from the G2.4.16 authorization-evidence store because authorization evidence and transition control have different identities and lifecycle meaning. It must reject unavailable roots, corrupt or incomplete records, invalid digests, symlinked or dangling record paths, unsafe locks, duplicates, and conflicting keys.

The milestone must not add a mutable completion state. Completion is an external fact requiring a future destination receipt/verification boundary. G2.4.17 only establishes the one pre-execution key whose state later authorities must respect.

## Failure matrix

| Condition | Required result | External effect |
|---|---|---|
| Missing, non-authorized, expired, altered, or invalid G2.4.16 evidence | `NOT_CONTROLLABLE` | None |
| Altered G2.4.15 / artifact / destination / policy binding | `NOT_CONTROLLABLE` | None |
| Unsupported transition profile or malformed idempotency key | `UNSUPPORTED_PROFILE` or `NOT_CONTROLLABLE` | None |
| New exact key and binding | `CLAIMED` | None |
| Same key and exact binding | `DUPLICATE` | None |
| Same key with different binding | `CONFLICT` | None |
| Existing ambiguous record | `AMBIGUOUS` | None; no automatic retry |
| Store unavailable/corrupt/incomplete/unsafe | Fail closed with typed storage finding | None |
| Caller requests upload, publish, deploy, release, retry, reconciliation, or rollback | No such G2.4.17 API exists | None |

## EBS-032 proposal

**EBS-032: Durable External Transition Control Ledger** should use only deterministic fakes and a temporary non-production control root. It must prove the following.

| Scenario | Required direct assertion |
|---|---|
| Exact G2.4.16 AUTHORIZED evidence and a fresh canonical key | One `CLAIMED` control decision; immutable record written. |
| Repeat exact request/key | `DUPLICATE`; no second record and no executor call. |
| Same key, changed artifact fingerprint, authorization, destination, policy, or transition intent | `CONFLICT`; no external action. |
| Missing, denied, expired, or altered authorization evidence | `NOT_CONTROLLABLE`; no claim. |
| Pre-seeded ambiguous record | `AMBIGUOUS`; no retry or progression. |
| Unavailable/corrupt/incomplete/symlinked record or unsafe lock | Fail closed; no claim. |
| Public capability audit | No `execute`, `upload`, `publish`, `deploy`, `release`, `retry`, `connect`, `request`, `issue_permit`, `create_session`, `consume`, `complete`, `reconcile`, or `rollback` capability. |
| Side-effect audit | Provider, network, credential, upload, destination, workspace mutation, command, runtime, session creation, permit issuance, audit-writer, and transition-execution counters all remain zero. |

## Acceptance criteria

A future implementation is acceptable only if it provides immutable self-validating contracts, a dedicated durable no-overwrite store, exact G2.4.16 authorization binding, canonical idempotency-key conflict protection, fail-closed storage behavior, and a deterministic benchmark that directly proves duplicate and ambiguous outcomes block automatic progression.

The milestone must remain opt-in: no CLI, autonomous, Chief, Coordinator, generic capability, session, invocation, runtime, workspace, audit, provider, or destination integration may import it. G2.4.9, G2.4.13, G2.4.14, G2.4.15, and G2.4.16 behavior must remain unchanged.

## Migration and integration impact

G2.4.17 should have **no migration** of current operational paths. Future work may require a separately approved destination-attestation/credential-egress boundary, then a bounded executor that consults this ledger before one external attempt, then an external receipt/verification/reconciliation design. Each of those steps must receive separate reconnaissance and authorization.

## Explicit deferrals

The following remain out of scope for G2.4.17: provider integration; registry client; upload, publish, deploy, or release; credential/secret handling; network access; destination discovery; endpoint or URL handling; runtime execution; session/permit issuance; workspace mutation; CLI/autonomous/Chief/Coordinator integration; a second approval or audit authority; external receipt creation; destination-side verification; reconciliation; rollback; and automated retry.

## Completion markers

```text
G2.4.17_RECON=COMPLETE
G2.4.17_DESIGN=COMPLETE
G2.4.17_IMPLEMENTATION=NOT_STARTED

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
```
