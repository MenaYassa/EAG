# G2.4.15 — Governed Artifact Promotion and Provenance Reconnaissance and Design

**Status:** Design only. **Baseline:** `6109e4301a99fe2a77842b6f8a9f22584bedf459`, tagged `v2.4.14-g2.4.14`.

> **Recommendation:** The safest next milestone is **G2.4.15 — Governed Artifact Promotion Eligibility Evidence Boundary**. It should be a library-only, immutable, read-only assessor that determines whether supplied READY artifact-readiness evidence, supplied lineage bindings, and a non-secret declared destination/intent are internally consistent. It must not execute or record a promotion, upload an artifact, publish a release, deploy a system, access credentials, create approval authority, or change runtime completion.

## 1. Decision summary

| Question | Design conclusion |
|---|---|
| Is an immediate next boundary needed? | **Yes, but only evidence eligibility.** G2.4.14 can establish artifact readiness, yet there is no immutable contract expressing a proposed transition’s exact artifact identity, destination identity, intent, and evidence continuity. |
| Recommended milestone | **G2.4.15 Governed Artifact Promotion Eligibility Evidence Boundary.** |
| Does it promote or publish anything? | **No.** It assesses evidence only and cannot create an `ArtifactTransitionReceipt`, because such a receipt would incorrectly imply that a transition occurred. |
| Is a complete provenance chain the next standalone milestone? | **No.** A full lifecycle provenance system is premature because the current artifact-readiness contracts do not prove causal physical generation by a governed execution. G2.4.15 should validate a narrowly declared, explicit lineage binding without overclaiming causality. |
| Is release execution appropriate now? | **No.** Registry upload, deployment, credentials, network egress, destination-side verification, and rollback are separate execution authorities not present in the published control plane. |
| Is environment readiness the better next step? | **No.** It has no bounded deployment target or separately authorized environment-test authority. It should be deferred until a concrete, controlled target model exists. |

## 2. FACT — published repository reality

The G2.4.14 boundary validates supplied immutable artifact snapshot, packaging, external validation receipt, and hygiene evidence. Its `READY` disposition is expressly an evidence-only conclusion that grants no execution or publication authority. Exact artifact fingerprinting binds an artifact identifier, snapshot identifier, root identity, manifest digest, and `pyproject.toml` digest; validation receipts bind to that exact fingerprint.[1]

The published G2.4.9 human approval receipt is also evidence-only, but it is bound to a prospective governed runtime session: activation receipt, execution/run identity, runtime request, provider policy, isolation binding, audit observer, and runtime identity. It is not a release- or destination-specific approval and must not be reinterpreted as one.[2]

G2.4.10 workspace custody and G2.4.11 runtime composition retain independent immutable attestation boundaries. G2.4.12 proves the intended deterministic ordering of custody, composition, activation, approval, session, invocation, and one supplied executor dispatch. G2.4.13 requires custody and composition readiness before session/replay claims. None of those milestones introduces artifact promotion, release recording, registry upload, deployment, or destination lifecycle authority.[3] [4] [5]

The legacy benchmark templates generate project files and packaging metadata through plan-step content, while the legacy workspace capability writes supplied content. These are generation/mutation concerns; they do not establish a released-artifact lifecycle.[6] The repository’s own package configuration uses Hatchling and provides a local `eag` console script, but the inspected project metadata and repository automation contain no implemented package-registry upload, release-publish, deployment, or promotion control path.[7]

The generic execution graph contains an `ArtifactNode` with a path, creator-worker identifier, version, and arbitrary metadata. It is not an immutable governed artifact identity, readiness proof, promotion intent, destination binding, or durable artifact provenance ledger.[8]

## 3. INFERENCE — remaining control-plane gap

A READY readiness assessment establishes that the **supplied artifact snapshot and supplied external receipts** satisfy a declared profile. It does not answer whether the same exact artifact is intended for a particular logical destination, whether the provided readiness assessment remains bound to the intended transition, or whether execution-era evidence was deliberately linked to the artifact being considered. A future release system would otherwise have no narrow evidence checkpoint between “artifact evaluated as ready” and “an external actor asks to transition it.”

A full provenance chain is not yet justified as a new durable store or release ledger. In particular, G2.4.14’s artifact-readiness request does not contain a causal execution receipt asserting that the governed runtime physically generated the artifact. Any contract that claimed to prove `request → activation → approval → custody → composition → readiness → artifact` as an already durable causal fact would overstate repository-supported evidence. The safe design is instead an immutable **declared lineage binding**: a caller supplies exact identifiers/digests from the published control-plane evidence and the assessor checks their self-consistency, including the exact READY artifact-readiness assessment. The result is eligibility evidence, not historical reconstruction or a release event.

## 4. Authority map

| Concern | Current owner | G2.4.15 boundary role | Explicit limit |
|---|---|---|---|
| Artifact creation and metadata/layout decisions | Existing generator/mutation workflow | None | Must not write, repair, or rearrange artifact files. |
| Artifact readiness | G2.4.14 | Consume and validate a supplied `READY` assessment bound to the exact artifact fingerprint | Must not rerun tests, builds, installs, or readiness validation commands. |
| Execution-era admission, approval, session, and invocation | G2.4.6.1, G2.4.9, G2.4.6.2/G2.4.8, G2.4.7.1 | Consume redacted identifiers/digests as declared lineage references only | Must not create sessions, permits, approval decisions, or dispatches. |
| Custody and composition | G2.4.10 and G2.4.11 | Consume attestation identifiers/digests as declared lineage references only | Must not re-attest a workspace or construct a runtime. |
| Artifact transition / promotion | **No current owner** | Produce only an eligibility assessment | Must not claim, perform, record, or finalize a transition. |
| Release publishing and deployment | **No current owner** | None | Must not upload, publish, deploy, access a registry, call an API, or use credentials. |
| Provenance recording | Existing evidence owners retain their records | Validate a supplied immutable linkage declaration | Must not become a universal provenance ledger. |

## 5. Candidate comparison

| Candidate | Architectural value | Primary risk | Recommendation |
|---|---|---|---|
| **A. Artifact Promotion Eligibility Evidence Boundary** | Adds the missing evidence checkpoint between exact READY artifact evidence and any future transition request. Can bind artifact fingerprint, readiness digest, declared source/destination identities, intent, and evidence references deterministically. | Could be mistaken for promotion authority if its output is named as a receipt or if destination identity contains credentials. | **Recommend.** Keep the output strictly eligibility-only. |
| **B. Full Artifact Provenance Chain** | Could later provide end-to-end lineage querying and audit correlation. | Premature causal claim: current artifact contracts lack a canonical runtime-to-artifact production receipt. A store adds durability/lifecycle ownership not required for the immediate gap. | Defer. Use only a declared, bounded lineage binding inside Candidate A. |
| **C. Release Execution Boundary** | Eventually necessary to upload, publish, or deploy. | Requires credentials, egress, destination APIs, execution controls, destination-side verification, failure recovery, and rollback. | Defer. It is a distinct high-risk authority. |
| **D. Environment Readiness Evidence** | Could eventually describe target compatibility. | No authorized environment probe/execution owner and no bounded deployment target model. | Defer until a future transition executor and destination model are separately designed. |
| **E. No immediate expansion** | Avoids new contracts. | Leaves no controlled evidence bridge before any future release-facing work begins. | Not preferred; Candidate A remains narrow and addresses a real gap. |

## 6. RECOMMENDATION — G2.4.15 scope and contracts

### 6.1 Purpose

G2.4.15 should answer only:

> “Does this exact READY artifact evidence have a valid, immutable, non-secret declared lineage and a well-formed proposed transition intent to a declared logical destination?”

Its output must **not** mean “the artifact was promoted,” “the destination accepted it,” “a release was published,” or “deployment succeeded.”

### 6.2 Proposed public contracts

| Contract | Purpose and required bindings | Forbidden capability |
|---|---|---|
| `PromotionIntentEvidence` | Immutable intent identifier; exact artifact identifier/fingerprint; source identity; logical destination identity; transition class; policy digest; requester/declared operator identity; schema version. Destination identity is logical and non-secret, not a URL with credentials or an authenticated client. | No destination connection, credential, upload, reservation, approval, or execution. |
| `ArtifactProvenanceEvidence` | Immutable declared lineage reference set: artifact fingerprint; G2.4.14 readiness assessment ID/digest; readiness request/snapshot IDs; optional execution-era identifiers and evidence digests for activation, approval, custody, composition, session, and invocation where a caller can supply them. | No record lookup, durable storage, reconstruction, or claim that an artifact was physically generated by an execution. |
| `PromotionEligibilityAssessment` | Immutable output containing identity, disposition (`ELIGIBLE`, `NOT_ELIGIBLE`, `UNSUPPORTED_TRANSITION`), typed findings, lineage references, recommendations, and canonical digest. | No `execute`, `promote`, `publish`, `upload`, `deploy`, `approve`, `retry`, `repair`, or transition-receipt method. |

`ArtifactTransitionReceipt` is explicitly **not** recommended for G2.4.15. It belongs only to a later, separately approved controlled transition executor, because it represents an external state change.

### 6.3 Read-only validation rules

The future assessor should fail closed unless all applicable rules hold:

1. The supplied G2.4.14 assessment is structurally valid, has disposition `READY`, and its digest verifies.
2. The intent, provenance declaration, readiness request, readiness snapshot, and readiness assessment reference the exact same artifact identifier/fingerprint and snapshot identity.
3. The destination identity and transition class are non-empty, policy-supported, canonical, and contain no credential-bearing or runtime-client material.
4. Every supplied control-plane reference is canonical and internally consistent. If an execution-era chain is declared, mismatched execution/run/runtime fields, altered binding digests, unknown evidence, or malformed references are rejected.
5. The contract distinguishes **missing optional execution-era provenance** from a false claim. The initial profile may support an explicitly bounded `artifact-readiness-lineage-v1`; any request requiring a complete governed execution lineage should receive `UNSUPPORTED_TRANSITION` until a canonical runtime-to-artifact production receipt exists.

### 6.4 Typed failure matrix

| Failure | Required disposition | Example finding |
|---|---|---|
| Readiness assessment missing, non-READY, corrupt, or digest mismatch | `NOT_ELIGIBLE` | `READINESS_EVIDENCE_INVALID` |
| Artifact ID, fingerprint, or snapshot mismatch | `NOT_ELIGIBLE` | `ARTIFACT_IDENTITY_MISMATCH` |
| Missing or altered lineage declaration | `NOT_ELIGIBLE` | `PROVENANCE_BINDING_MISMATCH` |
| Intent destination missing, malformed, non-canonical, or credential-bearing | `NOT_ELIGIBLE` | `DESTINATION_IDENTITY_INVALID` |
| Duplicate/conflicting intent identity | `NOT_ELIGIBLE` | `PROMOTION_INTENT_CONFLICT` |
| Unsupported transition class or requested complete-execution lineage profile | `UNSUPPORTED_TRANSITION` | `UNSUPPORTED_PROMOTION_PROFILE` |
| Any absent receipt, destination interaction, upload result, or deployment result | No inference permitted | No synthetic success finding or receipt. |

## 7. EBS-030 proposal — deterministic promotion eligibility rehearsal

**EBS-030: Governed Artifact Promotion Eligibility Evidence** should use only immutable synthetic fixtures and public G2.4.14 evidence contracts. It must not create a project, invoke a package tool, connect to a destination, or mutate a repository/workspace.

| Scenario | Required direct assertion |
|---|---|
| Valid READY artifact lineage plus canonical intent | `ELIGIBLE`; exact artifact fingerprint, readiness digest, lineage digest, source identity, and destination identity appear in the immutable assessment. |
| Altered artifact identity/fingerprint | `NOT_ELIGIBLE`; no eligibility assertion. |
| Missing, NOT_READY, or altered readiness assessment | `NOT_ELIGIBLE`. |
| Altered provenance binding or inconsistent declared execution-era reference | `NOT_ELIGIBLE`. |
| Unsupported complete-provenance profile | `UNSUPPORTED_TRANSITION`, not a false lineage claim. |
| Invalid destination or credential-like destination material | `NOT_ELIGIBLE`. |
| Side-effect guard | Provider calls, package uploads, registry/deployment calls, credential access, command executions, workspace/repository mutation, runtime calls, session creation, permit issuance, and audit writes all remain zero. |

## 8. Explicit deferrals

G2.4.15 must not include package publishing; PyPI, container-registry, or artifact-registry upload; deployment; CI/CD integration; secrets management; credential acquisition or handling; production release automation; destination API clients; CLI exposure; autonomous-path migration; artifact modification; template changes; workspace lifecycle operations; runtime execution; or a second approval/session/invocation authority.

A future release-execution design must first define a separate executor, destination credential boundary, egress policy, destination-side idempotency, external receipt model, rollback/recovery semantics, audit ownership, and human approval semantics specific to external release—not reuse the G2.4.9 pre-session approval as a release approval.

## 9. Acceptance criteria for a future implementation

A future G2.4.15 implementation is acceptable only if it introduces one isolated evidence-only package, immutable/canonical contracts, exact readiness and artifact binding, deterministic typed refusals, EBS-030, and zero side-effect authority. No existing runtime or control owner may import the package or be changed. The standalone benchmark must prove both an eligible evidence conclusion and every failure boundary before any future release executor is contemplated.

## 10. Reconnaissance disposition

```text
G2.4.15_RECON=COMPLETE
G2.4.15_DESIGN=COMPLETE
G2.4.15_IMPLEMENTATION=NOT_STARTED

SOURCE_CHANGES=0
TEST_CHANGES=0
BENCHMARK_CHANGES=0
REAL_PROVIDER_CALLS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
COMMAND_EXECUTIONS=0
NETWORK_INVOCATIONS=0
CREDENTIAL_ACCESS=0

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```

## References

[1]: ./src/eag/governed_artifact_readiness/models.py "G2.4.14 artifact readiness contracts"
[2]: ./src/eag/governed_approval/models.py "G2.4.9 governed approval receipt contract"
[3]: ./src/eag/governed_workspace/models.py "G2.4.10 workspace custody evidence"
[4]: ./src/eag/governed_composition/models.py "G2.4.11 runtime composition evidence"
[5]: ./tests/test_ebs_027_controlled_chain_rehearsal.py "G2.4.12 deterministic controlled-chain rehearsal"
[6]: ./src/eag/benchmark/templates.py "Deterministic benchmark artifact templates"
[7]: ./pyproject.toml "Current EAG package configuration"
[8]: ./src/eag/execution_graph/models.py "Generic execution-graph artifact model"
