# EAG G2.2 — EBS-014 Policy-Rejection Analysis

**Scope:** Analysis only. The prior one-shot diagnostic is the sole real-provider invocation used. No provider retry, implementation change, validator/policy/schema/prompt/provider configuration change, benchmark change, commit, push, or tag occurred.

> **Conclusion:** The retained sanitized evidence proves that the gateway rejected the internally parsed decision because at least one proposed dependency did not refer to a previously ordered plan step. However, the diagnostic artifact deliberately did not retain the plan’s step identities, ordinals, or dependency references. The actual dependency graph cannot therefore be reconstructed without inventing evidence or making a prohibited additional provider call. The only defensible final classification is **`ROOT_CAUSE=INSUFFICIENT_EVIDENCE`**.

## 1. Retained Sanitized Decision Evidence

The one-shot diagnostic retained the following facts and nothing more about the provider decision.

| Field | Retained value | Interpretation |
|---|---|---|
| Provider invoked | `true` | A real configured provider produced a response. |
| Structured output received | `true` | The output passed far enough through the structured path to reach policy validation. |
| Policy validation result | `failed` | Deterministic policy was invoked. |
| Terminal failure type/code | `policy_rejected` | The rejection was not a provider transport or schema failure. |
| Sanitized policy reason | `plan dependency must reference an earlier proposed step` | At least one dependency failed the policy’s ordered-reference condition. |
| Public EngineeringDecision returned | `false` | Expected: gateway withholds decisions rejected by policy. |
| Internal EngineeringDecision constructed | **Yes, inferred from control flow** | Parsing precedes policy validation. |
| Step list / step IDs / step titles | **Not retained** | Cannot reconstruct plan order. |
| Step dependency arrays | **Not retained** | Cannot identify invalid edge(s). |
| Raw response/prose | **Not retained** | Correctly excluded from sanitized diagnostic capture. |

## 2. Existing Policy Contract

The existing validator processes ordered plan steps from first to last. Before adding the current step ID to `seen_before`, it computes the current step’s dependencies that are not in `seen_before`. If any dependency target is absent from that prior-step set, it rejects the whole decision with `plan dependency must reference an earlier proposed step`.[1]

```text
POLICY_EXPECTATION=
For every step at ordinal n, every dependency reference must exactly equal the step_id
of a distinct step at an ordinal strictly less than n. A dependency on the current step,
a later step, or a nonexistent step is rejected.
```

This is an unambiguous ordered-plan policy. It accepts an ordinary topologically ordered dependency graph and rejects forward references, self-references, and dangling dependency IDs. No evidence shows that the validator maps semantic dependencies incorrectly; it compares the supplied dependency strings to the previously seen step IDs exactly as the contract specifies.[1]

## 3. Requested Step-by-Step Reconstruction

The requested reconstruction is not available from the retained sanitized diagnostic. The table is deliberately explicit rather than fabricated.

| Ordinal | Step identity/name | Capability | Dependency references | Target ordinal | Target exists | Target earlier | Result |
|---:|---|---|---|---:|---|---|---|
| 1..N | **Not retained** | **Not retained** | **Not retained** | **Not retained** | **Not retained** | **Not retained** | Cannot independently evaluate |

```text
STEP_ORDER=UNAVAILABLE_IN_RETAINED_SANITIZED_EVIDENCE
DEPENDENCY_GRAPH=UNAVAILABLE_IN_RETAINED_SANITIZED_EVIDENCE
ACTUAL_DECISION=INTERNALLY_PARSED_THEN_POLICY_REJECTED; STEP_GRAPH_NOT_RETAINED
VALID/INVALID=UNDETERMINED_AT_THE_EDGE_LEVEL
```

The terminal reason proves only the following existential statement:

```text
There existed at least one dependency reference in the submitted ordered plan
that was not a step ID present in the validator's prior-step set.
```

It does **not** identify whether that dependency was a forward reference, self-reference, nonexistent ID, typo, or another representation issue. It also does not identify the source step or target step. Those facts were not captured.

## 4. Independent Policy Evaluation

| Question | Answer | Evidence |
|---|---|---|
| Did the gateway invoke policy validation? | **Yes** | The diagnostic observed one policy-rejected event and the typed terminal code `policy_rejected`.[2] |
| Does the policy require earlier target steps? | **Yes** | The validator rejects `set(step.dependencies) - seen_before` when nonempty.[1] |
| Did at least one submitted dependency fail that predicate? | **Yes** | The exact retained policy reason states that condition.[2] |
| Can the exact invalid edge be identified? | **No** | No step/dependency summary was retained.[2] |
| Can the plan be declared objectively invalid as submitted? | **Not fully.** It was invalid *under the existing policy predicate*, but its actual graph cannot be independently inspected. | [1] [2] |
| Can a validator defect be established? | **No** | No conflicting semantic representation or edge data is available. |
| Can a contract-design problem be established? | **No** | The contract is coherent for sequential executable plans; no valid-but-rejected representation is available. |

## 5. Final Classification

```text
ROOT_CAUSE=INSUFFICIENT_EVIDENCE
```

The provider/gateway diagnostic gives enough evidence to locate the failure at deterministic dependency policy validation, but not enough to decide between the two hypotheses posed:

| Hypothesis | Finding |
|---|---|
| A. LLM generated an objectively invalid dependency graph | **Plausible but unproven.** The policy predicate was violated, yet the offending edge is unavailable. |
| B. Policy validator incorrectly rejected a semantically valid dependency representation | **Plausible but unproven.** No retained edge exists to show a valid semantic relationship that the contract misinterpreted. |

There is no evidence of a policy-validator defect. There is also insufficient retained evidence to conclusively attribute the fault to the LLM’s exact dependency graph. The correct analysis-only result is therefore insufficient evidence, not an inferred defect.

## 6. Hard Stop and Required Status

```text
PROVIDER_RETRIES_DURING_POLICY_ANALYSIS=0
PRODUCTION_BEHAVIOR_CHANGES=NONE
TEST_CHANGES=NONE
BENCHMARK_CHANGES=NONE
COMMITS=0
PUSHES=0
TAGS=0

G2.2_STATUS=OPEN
EBS_014_STATUS=FAIL
POLICY_ANALYSIS=COMPLETE
IMPLEMENTATION_CHANGES=NONE
```

## References

[1]: src/eag/chief/intelligence/gateway/validator.py "Ordered plan dependency validation"
[2]: /home/ubuntu/ebs014_single_diagnostic_result.json "Sanitized one-shot EBS-014 diagnostic result"
