# EAG G2.2 — Controlled EBS-014 Live Rerun Result

**Authorization:** One credentialed EBS-014 acceptance invocation.
**Execution count:** Exactly one authorized live acceptance invocation.
**Changes during run:** None. No source, validator, policy, prompt, provider configuration, selection, grounding evaluator, acceptance criterion, benchmark, commit, push, tag, or G2.3 change was made.

> **Result:** `EBS_014=FAIL`. The single real-provider acceptance invocation ended in a typed gateway provider-timeout failure before structured output, schema validation, policy validation, an `EngineeringDecision`, or grounding evaluation was reached.

## Sanitized Result

| Field | Value |
|---|---|
| EBS-014 result | `FAIL` |
| Failure stage | `gateway` |
| Failure code | `provider_timeout` |
| Sanitized reason | `Provider execution did not return a successful governed response.` |
| Gateway success | `false` |
| Provider invocation occurred | `true` |
| Structured output received | No; aggregate token usage was zero. |
| Schema validation | Not reached. |
| Policy validation | Not reached. |
| EngineeringDecision produced | No. |
| Grounding evaluation reached | No. |
| PolicyViolation | None; the timeout occurred before policy validation. |
| Aggregate prompt / completion / total tokens | `0 / 0 / 0` |
| Aggregate duration | `94,834.18 ms` |

## Safety Accounting

```text
REAL_PROVIDER_CALLS=1
CAPABILITY_EXECUTIONS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
SHELL_INVOCATIONS=0
COMMITS=0
PUSHES=0
```

## Required Result Markers

```text
EBS_014=FAIL
FAILURE_STAGE=gateway
FAILURE_CODE=provider_timeout
SANITIZED_REASON=Provider execution did not return a successful governed response.
POLICY_VIOLATION_STEP_ID=NOT_APPLICABLE
POLICY_VIOLATION_STEP_INDEX=NOT_APPLICABLE
POLICY_VIOLATION_DEPENDENCY_ID=NOT_APPLICABLE
POLICY_VIOLATION_DEPENDENCY_INDEX=NOT_APPLICABLE
REAL_PROVIDER_CALLS=1
CAPABILITY_EXECUTIONS=0
WORKSPACE_MUTATIONS=0
GIT_MUTATIONS=0
SHELL_INVOCATIONS=0
```

The run stops here. No retry or implementation action follows.
