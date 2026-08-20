# EAG G2.2 — Final Acceptance Assessment

**Assessment basis:** Completed deterministic validation, the credentialed EBS-013 regression, the authorized EBS-014 policy-rejection diagnostic, and the single controlled EBS-014 timeout rerun. No new provider call or repository change was made for this assessment.

> **Milestone status:** **G2.2 — Repository Intelligence: Implementation Complete; Live Acceptance Pending.** Future EBS-014 execution requires separate authorization and a reliable provider environment.

```text
G2.2_IMPLEMENTATION=COMPLETE
G2.2_LIVE_ACCEPTANCE=PENDING
EBS_014=UNRESOLVED_FAIL
```

> **Assessment:** The evidence supports **B — G2.2 implementation is substantially validated but live EBS-014 acceptance remains unresolved.** It does not support an acceptance pass, and the provider timeout must not be treated as a pass or as evidence of repository-grounding quality.

## 1. Evidence Summary

| Evidence area | Result | What it establishes |
|---|---|---|
| Deterministic G2.2 / gateway / policy tests | 26 policy-gateway tests; 40 targeted tests with 1 safe skip | Policy observability, dependency semantics, context safety, provenance, selection, and deterministic gateway contracts behave as specified. |
| Broader regressions | 3 autonomous tests; 6 EBS safe-lane tests with 2 credentialed skips; 3457 full tests with 3 skips | G2.2 changes preserved tested G2.0/G2.1 behavior across the repository. |
| Static quality | Ruff, MyPy, and `git diff --check` passed | The changed implementation is lint-clean, type-clean in touched modules, and whitespace-clean. |
| G2.1 live control | EBS-013 credentialed live regression passed | A valid governed structured decision can traverse the existing configured G2.1 gateway/provider path. |
| EBS-014 live attempt 1 | Provider returned structured output; schema parsing completed; policy rejected ordered-plan dependency | The repository context reached the provider. The decision violated the unchanged deterministic earlier-step dependency rule. Grounding evaluator was not reached. |
| EBS-014 live attempt 2 | Provider timeout; zero tokens; no structured output | Provider availability/reliability interrupted the run before schema, policy, decision, or grounding evaluation. |
| Read-only boundary | No capabilities, workspace mutations, Git mutations, shell invocations, commits, or pushes in either EBS-014 run | EBS-014 remained read-only. |

## 2. Deterministic G2.2 Implementation Correctness

The deterministic evidence does **not** identify a G2.2 repository-intelligence implementation defect. The first authorized EBS-014 diagnostic had complete selected evidence—route, service, test, symbols, dependencies, excerpts, fingerprints, and provenance—with no truncation or insufficiency. It reached the provider, parsed structured output, and reached deterministic policy validation. The rejection arose from the provider-generated ordered plan, not from repository discovery, source analysis, indexing, graph construction, selection, security/redaction, context projection, provenance, fingerprinting, or the grounding evaluator.

The subsequent policy-observability hardening added safe, structured `PolicyViolation` records without changing the dependency invariant. Deterministic tests verified forward, unknown, and self dependencies reject, while valid and duplicate-earlier dependency behavior remains unchanged. This materially improves diagnosis of future policy rejections, but it does not retroactively make EBS-014 pass.

**Assessment:** **Substantially validated.** The deterministic implementation does not warrant a new implementation fix based on present evidence.

## 3. G2.1 Governed Gateway Correctness

The G2.1 gateway behaved correctly in both relevant observed paths.

| Live outcome | Gateway behavior | Assessment |
|---|---|---|
| EBS-013 valid decision | Returned a validated decision | Correct valid-path behavior. |
| EBS-014 attempt 1 invalid dependency sequence | Parsed structured decision, applied unchanged policy, rejected it before exposing a public decision or grounding evaluation | Correct rejection-path behavior. |
| EBS-014 attempt 2 provider timeout | Returned typed `provider_timeout` without an EngineeringDecision, schema/policy evaluation, or grounding evaluation | Correct containment of an unavailable provider response. |

The policy rejection is not evidence that the gateway incorrectly rejected a semantically valid plan. The initial diagnostic established only that the provider proposed a dependency not acceptable under the existing ordered-step policy. The later safe violation record makes such future cases diagnosable by preserving step and dependency identifiers without retaining raw provider output.

**Assessment:** **Correctly governed and substantially validated.**

## 4. Live Provider Availability and Reliability

The two EBS-014 live outcomes demonstrate that the configured provider path is not a reliable acceptance oracle in the observed environment.

Attempt 1 completed enough of the call to produce structured output, but the output’s dependency order was policy-invalid. Attempt 2 timed out before returning any structured output, with aggregate token usage of zero. The timeout provides no evidence for or against repository grounding because grounding evaluation was never reached.

This pattern does not prove the provider is universally unavailable; EBS-013 passed live, and EBS-014 attempt 1 returned a structured response. It does prove that **the two authorized EBS-014 runs did not yield an accepted, policy-valid, grounding-evaluable decision**.

**Assessment:** **Live provider availability/reliability is insufficient for EBS-014 acceptance closure in the observed controlled runs.**

## 5. EBS-014 Repository-Grounding Acceptance

EBS-014 cannot be marked as accepted. Neither authorized live attempt reached a successful governed decision followed by the existing grounding evaluator.

| Attempt | Provider outcome | Gateway outcome | Grounding evaluator | Grounding acceptance conclusion |
|---|---|---|---|---|
| 1 | Structured output received | Policy rejection: dependency did not reference an earlier proposed step | Not reached | No grounding acceptance evidence. |
| 2 | Timeout; no structured output | Typed `provider_timeout` | Not reached | No grounding acceptance evidence. |

The first attempt does show that the provider received enough context to formulate a structured engineering decision. It does **not** demonstrate grounding acceptance because policy rejection prevents the evaluator from running. The second attempt is operationally inconclusive for grounding.

**Assessment:** **EBS-014 acceptance remains unresolved and currently fails.**

## 6. Decision and Recommendation

```text
SUPPORTED_OPTION=B. G2.2 implementation substantially validated but live acceptance unresolved
```

The recommended disposition is **Option 2: close G2.2 as implementation-complete but live-acceptance-pending**. This is not an `EBS_014=PASS`; it preserves the distinction between the validated deterministic implementation and the unresolved live acceptance benchmark. A future controlled environment may retry EBS-014 only under separate explicit authorization and an operationally reliable provider path.

A deterministic implementation fix is **not** recommended from the current evidence. A provider timeout is not an implementation defect, and the prior policy rejection was correctly governed under the unchanged invariant. Keeping the whole implementation open indefinitely would understate the deterministic evidence; marking EBS-014 as accepted would overstate the live evidence.

## 7. Required Final Markers

```text
G2.2_IMPLEMENTATION=COMPLETE
G2.2_LIVE_ACCEPTANCE=PENDING
EBS_014=UNRESOLVED_FAIL
G2.2_IMPLEMENTATION_ASSESSMENT=SUBSTANTIALLY_VALIDATED_LIVE_ACCEPTANCE_PENDING
EBS_014_ACCEPTANCE=UNRESOLVED_FAIL
LIVE_PROVIDER_STATUS=UNRELIABLE_FOR_EBS014_ACCEPTANCE_IN_OBSERVED_RUNS
IMPLEMENTATION_CHANGES=NONE
EBS_014_FURTHER_RUNS=NONE
G2.3=NOT_STARTED
COMMIT=NOT_PERFORMED
```
