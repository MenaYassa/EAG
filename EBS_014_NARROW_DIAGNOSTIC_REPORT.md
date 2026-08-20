# EAG G2.2 — EBS-014 Narrow Diagnostic Report

**Date:** 20 August 2026
**Scope:** Exactly one credentialed real-provider diagnostic invocation using the existing EBS-014 fixture, repository-aware context path, configured gateway, model selection, schema, policy, and benchmark request shape.
**Safety:** No raw prompt, provider body, source content, secrets, credentials, or sensitive environment values were captured. No production source, tests, acceptance criteria, provider configuration, commit, push, or tag was changed.

> **Exact root cause:** The provider returned structured output that passed schema parsing and reached deterministic gateway policy validation. The decision was then rejected because a proposed plan step declared a dependency that did not reference an **earlier** proposed step. The exact policy reason was: `plan dependency must reference an earlier proposed step`.

## 1. One-Shot Execution Record

| Diagnostic field | Sanitized observed value |
|---|---|
| Credential availability | Available through the existing configured live-provider path |
| Authorized diagnostic invocations | **1** |
| Provider invocation occurred | `true` |
| Gateway success | `false` |
| Failure type | `policy_rejected` |
| Failure code | `policy_rejected` |
| Failure stage | `policy_validation` |
| Sanitized failure message | `Validated provider response was rejected by deterministic decision policy.` |
| Policy rejection reason | `plan dependency must reference an earlier proposed step` |
| Structured output received | `true` |
| Schema validation result | **Passed sufficiently to reach policy validation** |
| Policy validation result | **Failed** |
| EngineeringDecision produced internally | **Yes.** Parsing necessarily returned a decision before policy validation executed. |
| EngineeringDecision exposed in result | **No.** The gateway correctly returns no public decision after policy rejection. |
| Grounding evaluator reached | `false` |
| Context fingerprint continuity | `true` |
| Snapshot fingerprint continuity | `true` |

The trace recorded one context-assembled event, one routing-selected event, one provider attempt-started event, one policy-rejected event, one attempt-failed event, and one gateway-failed event. It recorded zero response-validated and zero gateway-completed events. This ordering confirms that the decision reached parsing and policy validation but was not accepted as a governed result.

## 2. Aggregate Provider Usage

| Usage measure | Value |
|---|---:|
| Prompt tokens | 2,057 |
| Completion tokens | 3,284 |
| Total tokens | 5,341 |
| Estimated cost | 0.0 |
| Duration | 27,733.56 ms |

The selected evidence count remained four files, nine symbols, five dependencies, and four excerpts, with zero omitted items. These values match the prior deterministic forensic reconstruction; the diagnostic did not reveal a context shortfall, truncation, or fingerprint discontinuity.

## 3. Classification

```text
SELECTED_CLASSIFICATION=D. Policy validation failure
FAILURE_TYPE=policy_rejected
FAILURE_CODE=policy_rejected
FAILURE_STAGE=policy_validation
SANITIZED_REASON=plan dependency must reference an earlier proposed step
```

The diagnostic rules out the following alternatives for this execution:

| Alternative | Result | Evidence |
|---|---|---|
| A. Provider transport/runtime failure | **Ruled out** | Provider invocation occurred and nonzero aggregate completion usage was returned. |
| B. Provider returned invalid structured output | **Ruled out for this run** | The gateway reached `validate_decision_policy`, which occurs after strict JSON/schema parsing. |
| C. Schema validation failure | **Ruled out for this run** | No `schema_invalid` event occurred; the policy-rejected event did. |
| D. Policy validation failure | **Confirmed** | Gateway emitted `policy_rejected` with the exact sanitized reason. |
| E. EngineeringDecision construction failure | **Ruled out** | A decision was constructed internally before policy validation. |
| F. Gateway orchestration bug | **Not indicated** | The gateway followed its intended parse → deterministic policy → reject flow. |
| G. Other typed gateway failure | **Ruled out** | Typed terminal kind was `policy_rejected`. |
| H. Insufficient evidence | **Ruled out** | The diagnostic captured the typed terminal event and validation reason. |

## 4. Relation to EBS-014

The failed decision was not accepted and therefore the benchmark’s grounding evaluator did not run. This outcome does **not** establish a repository-context, selection, provenance, fingerprint, schema, or grounding-evaluator defect. It establishes that the provider-generated ordered plan violated an existing deterministic governed-decision constraint: each plan-step dependency must name a step that appears earlier in the same proposed plan.

The provider’s plan ordering/dependency error is distinct from a factual grounding failure. Because the decision was rejected before result construction, no provider claims or citations were exposed to the EBS-014 evaluator. No benchmark rule was weakened, no provider output was transformed, and no failure was converted to success.

## 5. Hard-Stop Confirmation

```text
DIAGNOSTIC_INVOCATIONS=1
PRODUCTION_BEHAVIOR_CHANGES=NONE
TEST_CHANGES=NONE
BENCHMARK_CRITERIA_CHANGES=NONE
PROVIDER_CONFIGURATION_CHANGES=NONE
COMMITS=0
PUSHES=0
TAGS=0
```

## 6. Required Final Status

```text
G2.2_STATUS=OPEN
EBS_014_STATUS=FAIL
DIAGNOSTIC=COMPLETE
IMPLEMENTATION_CHANGES=NONE
```
