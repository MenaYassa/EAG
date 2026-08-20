# EAG G2.2 — Policy Observability Hardening Report

**Date:** 20 August 2026
**Scope:** Deterministic policy-validation observability only.
**Baseline:** Existing G2.2 worktree at `98494201bec6ad684a03f89a8232331a3ae77cba`.

> **Result:** Future deterministic policy rejections now retain a safe, structured `PolicyViolation` record in the failed `EngineeringDecisionResult` and `GatewayPolicyRejected` event. Dependency semantics are unchanged. No EBS-014 live rerun occurred.

## 1. Delivered Observability Contract

The gateway now exposes an additive immutable `PolicyViolation` record with a stable `PolicyViolationCode`, `stage`, sanitized message, affected step ID, dependency step ID, affected step index, dependency target index where known, policy contract version, and decision schema version.

| Contract element | Result |
|---|---|
| Stable violation code | Added `PolicyViolationCode`, including `dependency_not_earlier_step`. |
| Validation stage | Recorded as `policy_validation`. |
| Safe message | Retains only deterministic validator wording. |
| Step identity/index | Captures `step_id` and zero-based `step_index` where applicable. |
| Dependency identity/index | Captures the structured dependency ID and its plan index when it exists; `None` for unknown IDs. |
| Contract/schema version | Records policy contract `1.0` and the decision schema version. |
| Event propagation | `GatewayPolicyRejected` retains both legacy `reason` and structured `violation`. |
| Public result propagation | Failed `EngineeringDecisionResult` retains optional `policy_violation`; successful results reject such payloads. |

The record intentionally contains **no raw provider body, raw prompt, source code, credentials, secrets, sensitive environment data, or unbounded repository content**. Structured step IDs and dependency IDs are retained as the authorized diagnostic metadata.

## 2. Dependency Semantics Preserved

The dependency invariant remains exactly unchanged:

```text
Every dependency must reference a distinct earlier proposed step_id.
```

The validator still rejects forward references, unknown references, and self-references. It does not reorder steps, repair decisions, make forward dependencies valid, or alter any accepted decision. Duplicate dependencies that reference an already-earlier step remain accepted, matching the prior set-based behavior.

## 3. Deterministic Test Coverage

The gateway contract suite now verifies all requested policy-observability cases.

| Case | Result |
|---|---|
| Valid ordered dependency graph | Passes without a violation. |
| Later-step dependency | Rejected with `dependency_not_earlier_step`, source/target IDs, and ordinals. |
| Unknown dependency | Rejected with the stable code, source/target IDs, source ordinal, and no target ordinal. |
| Self-dependency | Rejected with the stable code and matching source/target ordinal. |
| Duplicate earlier dependency | Continues to pass; no semantic change. |
| Stable code and sanitized IDs | Asserted directly. |
| No raw provider content retention | A synthetic provider-body marker is absent from the `PolicyViolation` and rejection event representations. |
| Missing EBS-014 diagnostic fields | Future forward-reference rejection now exposes the exact step/dependency metadata that was previously unavailable. |
| Existing policy behavior | Original deterministic policy and gateway tests remain green. |

## 4. Validation Results

| Validation | Result |
|---|---|
| Policy and gateway deterministic suite | **26 passed** |
| G2.2 context + gateway + normal EBS-014 lane | **40 passed, 1 skipped** |
| EBS suite, normal non-live lane | **6 passed, 2 skipped** |
| EBS-013 credentialed live regression | **1 passed**; only LiteLLM event-loop deprecation warning |
| Dedicated autonomous suite | **3 passed** |
| Full pytest suite | **3457 passed, 3 skipped** in 35.07 seconds |
| Ruff, touched files | **PASS** |
| MyPy, touched gateway source files | **PASS** — 6 source files checked |
| `git diff --check` | **PASS** |
| EBS-014 live rerun in this phase | **NO** |

## 5. Files Changed

| File | Change |
|---|---|
| `src/eag/chief/intelligence/gateway/errors.py` | Added stable policy violation codes, immutable safe `PolicyViolation`, and a typed `PolicyValidationError`. |
| `src/eag/chief/intelligence/gateway/models.py` | Added optional safe `policy_violation` to failed results. |
| `src/eag/chief/intelligence/gateway/validator.py` | Preserved all policy predicates while constructing structured violations. |
| `src/eag/chief/intelligence/gateway/events.py` | Added violation metadata to policy-rejection events. |
| `src/eag/chief/intelligence/gateway/runtime.py` | Propagates policy violations to the existing failure event/result path. |
| `src/eag/chief/intelligence/gateway/__init__.py` | Exports the new public observability contracts. |
| `tests/test_governed_gateway.py` | Adds deterministic safety, dependency, and diagnostic-regression tests. |

## 6. Explicit Non-Changes

```text
POLICY_SEMANTICS_CHANGED=NO
EBS_014_RERUN=NO
EBS_014_ACCEPTANCE_CRITERIA_CHANGED=NO
PROVIDER_CONFIGURATION_CHANGED=NO
PROVIDER_PROMPT_CHANGED=NO
CONTEXT_SELECTION_CHANGED=NO
GROUNDING_EVALUATOR_CHANGED=NO
G2.3_STARTED=NO
COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_PERFORMED
```

## 7. Required Final Status

```text
POLICY_OBSERVABILITY=COMPLETE
POLICY_SEMANTICS_CHANGED=NO
EBS_014_RERUN=NO
EBS_014_STATUS=FAIL
G2.2_STATUS=OPEN
COMMIT=NOT_PERFORMED
```
