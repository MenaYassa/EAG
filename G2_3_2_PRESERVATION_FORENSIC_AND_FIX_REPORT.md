# EAG G2.3.2 — Full-File Preservation Forensic and Deterministic Fix Report

**Date:** 21 August 2026
**Baseline milestone:** [`v2.3.1-g2.3.1`](https://github.com/MenaYassa/EAG/tree/v2.3.1-g2.3.1) at `e309710a10fbcac1c90ed7005f0978c40935236d`
**Scope:** A deterministic, pre-authorization rejection safeguard for one controlled full-file replacement. This work does not commit, push, tag, re-run EBS-014, re-run live EBS-015, modify generic capability dispatch, modify `WorkspaceCapability`, add shell/Git/network capability, or mutate the EAG source repository.

> **Conclusion:** The live failure exposed an **underspecified full-file preservation contract**. The fix adds a trusted preservation binding that can reject an incomplete provider replacement before a `ChangeProposal` reaches G2.3.1 policy or one-time authorization. It does not merge, repair, patch, infer, relocate, or otherwise alter provider content.

## 1. Forensic Finding

The provider mutation field is `MutationIntent.proposed_content`. The translator copies that string unchanged into `ChangeProposal.content`; it does not construct a patch or modify the content. Trusted precondition state is derived from the existing target’s exact UTF-8 fingerprint. The expected postcondition is the fingerprint of the provider-supplied replacement. G2.3.1 therefore correctly proves that the file was unchanged before the write and exactly matches the authorized proposal afterward.

| Investigation question | Finding |
|---|---|
| Exact provider field | `mutation_intents[0].proposed_content` is the complete replacement field. |
| Route to proposal | `DecisionToChangeProposalTranslator.translate` maps `proposed_content` directly to `ChangeProposal.content`. |
| Trusted precondition | `TrustedWorkspaceState.read_target_state` reads the confined target and derives its SHA-256 fingerprint before proposal construction. |
| Expected postcondition | The translator derives it from the proposed content fingerprint; G2.3.1 checks the written target against both the expected fingerprint and proposal content fingerprint. |
| Original target evidence | Before the fix, the translator read the original target but retained only existence and fingerprint for proposal construction. |
| Exact benchmark judgment | Live EBS-015 compares the final disposable fixture manifest to the exact expected `article.py` content, including the original module docstring. |
| Existing distinction capability | The old contract could distinguish stale targets and mismatched written content, but not complete replacement versus accidental omission versus intentional deletion. |
| Preservation statement | The old prompt said “full replacement” but did not state that unrelated pre-existing content must be retained, and the typed intent did not bind such retention. |

The first live attempt was not a mutation runtime defect: gateway validation, translation, policy, authorization, atomic write, receipt, and runtime postcondition verification all succeeded. It was not a benchmark mismatch: the benchmark accurately asserted the desired full target state. The provider had submitted a valid full replacement under an incomplete contract, but that replacement omitted the unrelated leading module docstring.

```text
ROOT_CAUSE_CLASSIFICATION=UNDERSPECIFIED_LLM_FULL_FILE_REPLACEMENT_CONTRACT
```

## 2. Smallest Safe Fix

The correction belongs jointly to **the mutation-intent structured-output contract** and **the read-only translator**, not to generic workspace execution, G2.3.1 mutation mechanics, the benchmark evaluator, or a future G2.4 capability.

| Component | Deterministic correction |
|---|---|
| Trusted request policy | `PreservationRequirement` defines an immutable requirement ID plus an exact required leading text region. `MutationIntentPolicy` carries a tuple of these trusted requirements. |
| Provider contract | A mutation intent must include `preservation_requirement_ids`. The strict JSON schema requires the field. The gateway policy requires it to equal the trusted configured requirement IDs exactly. |
| Provider instruction | Mutation-intent mode explicitly states that each configured leading source region must be retained verbatim and its ID declared. |
| Read-only translator | Before proposal creation, the translator reads the confined existing target, verifies that each trusted requirement actually matches the target’s leading content, and verifies that the provider’s `proposed_content` begins with the same trusted content. Any mismatch is a sanitized `preservation_requirement_invalid` translation failure. |
| Existing governed boundary | Only after that rejection gate succeeds does the translator form the unchanged G2.3.1 `ChangeProposal`; existing policy, one-time authorization, atomic write, receipt, and postcondition verification remain authoritative. |

The first controlled EBS-015 request binds only one exact leading prefix: the fixture module docstring plus the following blank line. This is intentionally bounded. It detects the observed omission, but does not claim to infer arbitrary semantic “unrelated content” in an unconstrained file. Future broader preservation needs require a separately designed trusted-region model rather than hidden fuzzy matching.

## 3. Why the Fix Is Safe

The system rejects; it never repairs. Trusted composition selects the preserved leading region. The provider declares only its opaque requirement ID, has no workspace root or filesystem handle, and still supplies the complete replacement text. The translator uses a confined read solely to compare exact text. It does not concatenate the original content with model output, apply a patch, fill gaps, move content, or issue another model call.

A rejected replacement has no `ChangeProposal`, no `MutationReceipt`, no authorization event, no authorization consumption, and no workspace mutation. The existing runtime remains responsible for all effects, only after the translator has accepted a complete bound replacement.

```text
LLM_AUTHORITY=NONE
TRANSLATOR=PURE_READ_ONLY
CHANGE_PROPOSAL=UNTRUSTED
MUTATION_POLICY=AUTHORITATIVE
AUTHORIZATION=EXACT_ONE_TIME
MUTATION=ATOMIC_BOUNDED
VERIFICATION=DETERMINISTIC
RECEIPT=REDACTED
```

## 4. Deterministic Regression Protection

The new deterministic tests prove the requested failure and success boundaries.

| Test coverage | Result |
|---|---|
| Complete replacement retaining the trusted prefix is accepted, reaches the existing runtime, produces a completed receipt, and writes the exact full content. | PASS |
| Replacement that declares the trusted ID but omits the protected module prefix is rejected in the translator. | PASS |
| Rejection occurs before `ChangeProposal` creation, mutation policy, authorization, and workspace write. | PASS |
| Rejected proposal causes no `MutationAuthorized` event and leaves the target unchanged. | PASS |
| Gateway policy rejects a missing required preservation binding before translation. | PASS |
| Existing G2.3.1 mutation safety tests remain green. | PASS |
| G2.2/G2.1/G2.0 and autonomous regressions remain green. | PASS |
| Live EBS-015 remains explicit opt-in and was not called during this validation. | PASS |

## 5. Files Changed

| Area | Files |
|---|---|
| Typed intent / trusted request policy | `src/eag/chief/intelligence/gateway/models.py` |
| Stable gateway policy diagnostics | `src/eag/chief/intelligence/gateway/errors.py` |
| Strict schema and policy binding check | `src/eag/chief/intelligence/gateway/validator.py` |
| Provider-facing preservation obligation | `src/eag/chief/intelligence/gateway/runtime.py` |
| Read-only pre-proposal preservation rejection | `src/eag/chief/intelligence/gateway/mutation_translation.py` |
| Public API export | `src/eag/chief/intelligence/gateway/__init__.py` |
| Deterministic G2.3.2 coverage | `tests/test_governed_decision_mutation.py`, `tests/test_governed_gateway.py` |
| Live benchmark request binding only | `tests/test_ebs_015_llm_governed_mutation.py` |
| Closeout documentation | `G2_3_2_PRESERVATION_FORENSIC_AND_FIX_REPORT.md` |

## 6. Validation Evidence

| Validation | Result |
|---|---|
| G2.3.2 + G2.3.1 + G2.2 targeted group | **89 passed, 2 skipped**. EBS-014 and live EBS-015 stayed disabled. |
| Autonomous suite | **3 passed**. |
| Normal EBS suite | **7 passed, 3 skipped**. EBS-013, EBS-014, and live EBS-015 remained opt-in. |
| Full pytest suite | **3506 passed, 4 skipped**. |
| Ruff | **PASS**. |
| MyPy | **PASS** for `src/eag/chief/intelligence/gateway` (11 source files). |
| Whitespace | `git diff --check`: **PASS**. |
| Live provider calls in this task phase | **0**. |

## 7. Live EBS-015 Status and Required Stop

The prior live EBS-015 result remains **FAIL** for its exact poststate assertion. The deterministic contract now addresses the observed omission by rejecting it before authorization and mutation. That behavior has not been proven with a new provider response because the user explicitly prohibited another call without renewed authorization.

```text
EBS_015_STATUS=PREVIOUS_LIVE_FAIL_REMEDIATED_DETERMINISTICALLY
EBS_015_RETRY_REQUIRED=YES
REASON=The new typed preservation binding and pre-authorization translator rejection must be verified once against a fresh provider response in the existing disposable exact-poststate benchmark.
EXPECTED_PROVIDER_CALLS=1
AUTHORIZATION=ONE_TIME
NO_AUTOMATIC_RETRY=TRUE

EBS_014_RERUN=NO
LIVE_PROVIDER_CALLS_THIS_PHASE=0
COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```

No new live call was made. A future attempt, if separately authorized, must use the existing explicit opt-in EBS-015 lane, one provider call, one disposable fixture workspace, exact before/after manifest assertions, exact changed-path assertion, and no EAG source repository mutation.
