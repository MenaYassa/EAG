# G2.1 Governed LLM Gateway — Implementation Report

**Implementation date:** 20 August 2026
**Baseline:** `v2.0.0-g2.0` at `8ce2ba953854995ed179ac55a1c049dd4bae0f33`
**Implementation status:** **Complete; uncommitted and unpushed**

> **Approved boundary preserved.** The gateway produces a validated, advisory `EngineeringDecision`. It does not execute a capability, mutate a workspace or Git repository, replace the deterministic `DefaultPlanner`, change the default CLI path, or start G2.2.

## 1. Outcome Summary

The first G2.1 milestone is implemented. The new gateway composes existing `IntelligenceRuntime` model selection and `ExecutionRuntime` provider transport behind an explicit, typed decision boundary. The public outcome is either a schema- and policy-validated `EngineeringDecision` or a normalized safe failure; it is never an executable `Plan` or `CapabilityRequest`. The deterministic `DecisionToPlanTranslator` is available as a separate, non-effectful conversion step, while existing Coordinator and CapabilityRuntime governance remains unchanged. [1] [2] [3]

| Delivery area | Outcome |
|---|---|
| Governed domain boundary | Implemented as immutable request, context, decision, risk, step, trace, usage, policy, result, and error models. |
| Selection and provider transport | Integrated through existing `IntelligenceRuntime`, `ExecutionRuntime`, and the LiteLLM adapter. [4] [5] |
| Structured output | Provider receives a strict JSON Schema; local parsing and deterministic policy validation remain the authority. |
| Safe failure | Routing, provider, schema, policy, timeout, and budget outcomes return a failed `EngineeringDecisionResult` with no decision. |
| Deterministic planning default | Preserved. No `LLMPlanner`, factory wiring, Chief/Coordinator change, or default CLI behavior change was made. |
| EBS-013 | Implemented as a real-provider, explicit-opt-in integration benchmark and passed in the credentialed validation run. |

## 2. Files Changed

| File or area | Change |
|---|---|
| `src/eag/chief/intelligence/gateway/models.py` | Added immutable engineering decision, context, policy, trace, usage, request, result, risk, and proposed-step models. |
| `src/eag/chief/intelligence/gateway/{errors,events,protocol,context,validator,runtime,translator}.py` | Added normalized failures, redacted lifecycle events, public protocol, context-assembly seam, strict schema parser, policy validator, runtime integration, and deterministic translator. |
| `src/eag/chief/intelligence/gateway/__init__.py` | Added the focused public gateway API. |
| `src/eag/chief/intelligence/execution/models.py` | Added immutable optional `response_schema` transport metadata. |
| `src/eag/chief/intelligence/execution/providers/litellm_provider.py` | Added provider-neutral response-schema forwarding and propagated execution timeout to LiteLLM; no engineering-domain logic was added. |
| `src/eag/config/settings.py` | Added frozen, explicitly disabled-by-default `GatewaySettings`. |
| `tests/test_governed_gateway.py` | Added focused model, schema, policy, retry, fallback, budget, safe-failure, event, usage/trace, translation, fake-gateway consumer, and configuration tests. |
| `tests/test_ebs_013_governed_decision.py` | Added live EBS-013. It requires `EAG_EBS013_LIVE=1` and credentials, so normal/local runs distinctly skip it. |
| `tests/test_chief_intelligence_litellm.py` | Added strict response-schema forwarding coverage and updated timeout expectations. |
| `docs/architecture/G2.1_GOVERNED_LLM_GATEWAY_DESIGN.md` | Retained the approved architecture contract as an uncommitted design artifact. |

## 3. Implemented Architecture

The runtime path is intentionally layered. `GatewayRuntime.decide()` first sends a structured-output requirement to existing model selection. It then builds an `ExecutionContext` carrying a strict JSON Schema and bounded provider options, delegates the call/retry/fallback mechanics to `ExecutionRuntime`, locally parses the provider content, runs deterministic policy validation, and emits a redacted result/event trace. [4] [5]

```text
EngineeringDecisionRequest
  → IntelligenceRuntime.select_model()
  → ExecutionRuntime.execute()
  → LiteLLMProvider (transport only)
  → strict JSON parser
  → deterministic policy validator
  → EngineeringDecisionResult
  → optional DecisionToPlanTranslator
  → existing Coordinator / CapabilityRuntime only if a later caller elects to govern execution
```

The gateway does **not** import `CapabilityRuntime`, instantiate a workspace/repository runtime, or call a capability. Its only `.execute()` call targets the existing provider execution runtime. The translator creates a normal `Plan` value but does not execute that plan. [2] [3]

## 4. Public Contracts and Validation Rules

| Contract | Implemented rule |
|---|---|
| `EngineeringDecisionRequest` | Requires a non-empty goal, immutable `EngineeringContext`, unique non-empty capability allowlist, structured-output requirement, supported schema version, and bounded `GatewayPolicy`. |
| `EngineeringDecision` | Requires an interpreted goal, approach, at least one step, at least one required capability, at least one risk, valid confidence `[0, 1]`, and current schema version. |
| `ProposedPlanStep` | Carries an advisory step ID, title, capability reference, earlier-step dependencies, optional parameters, and expected evidence. It is not a `PlanStep` or `CapabilityRequest`. |
| Schema validation | Rejects malformed JSON, non-object payloads, unknown/missing contract fields, malformed steps/risks, invalid severity, invalid confidence, missing plan, or missing risk disclosure. |
| Policy validation | Rejects capabilities outside the caller allowlist, duplicate IDs, forward/unknown dependencies, capability-set mismatches, and executable parameter semantics such as `command`, `shell`, `code`, `script`, or tool-call keys. |
| Safe failure result | A failure always includes a typed `GatewayError`; it never exposes a partially validated decision. |

The canonical provider schema uses strict JSON output with `additionalProperties: false`. Provider-native schema enforcement is an optimization; local validation is mandatory. To satisfy the configured provider’s strict-schema rule that every declared property be required, step `parameters` is optional in the provider schema and defaults to an empty mapping locally. This retains the non-executable policy boundary while avoiding a provider-rejected schema.

## 5. Provider Integration, Retry, Fallback, and Telemetry

The integration preserves current ownership. `IntelligenceRuntime` selects an explainable compatible model; `ExecutionRuntime` remains responsible for health, retry, ordered fallback, usage, pricing, and transport tracing. The gateway enforces decision-level requirements and converts expected failures into `GatewayErrorKind` outcomes. [4] [5]

| Concern | Implemented behavior |
|---|---|
| LiteLLM | Stays a leaf provider adapter. It receives generic `ExecutionContext` content/options and returns generic `ExecutionResult`. [6] |
| Structured output | `ExecutionOptions.response_schema` is passed as LiteLLM/OpenAI-compatible `response_format.json_schema` with `strict: true`. |
| Timeout | Existing `ExecutionOptions.timeout_ms` now propagates to LiteLLM’s transport timeout parameter. |
| Retry | Gateway policy sets the execution retry count; timeout failures are normalized as `PROVIDER_TIMEOUT`. |
| Fallback | Only alternatives selected as structured-output-compatible models are offered to execution. A fallback to the same provider but a different model is correctly recorded in the gateway trace. |
| Budget | Total tokens and estimated cost are checked after a successful provider response and before a decision is accepted. |
| Tracing | Gateway events carry request/trace IDs, provider/model IDs, counts, state, and usage. They exclude raw prompts, raw responses, API keys, and source text. |

## 6. Test and Validation Evidence

| Gate | Result | Evidence |
|---|---:|---|
| Full repository suite | **3435 passed, 2 skipped** | `uv run pytest -q` |
| New G2.1-focused suite | **31 passed, 2 skipped** | Gateway unit tests, EBS-013 safe-mode skip, and LiteLLM adapter tests. |
| Core gateway suite | **18 passed** | Models, parser, policy, retry/fallback, timeout, budget, events, translation, and consumer-contract coverage. |
| Autonomous regression | **150 passed** | Canonical G2.0 composition, loop, and recovery/approval tests. |
| EBS suite in safe mode | **6 passed, 1 skipped** | Existing EBS tests passed; EBS-013 skipped without explicit live opt-in. |
| EBS-013 live benchmark | **1 passed** | `EAG_EBS013_LIVE=1 uv run pytest -q tests/test_ebs_013_governed_decision.py` using a real configured LiteLLM/OpenAI-compatible endpoint. |
| Ruff, touched files | **Passed** | All G2.1 touched source/test files clean. |
| MyPy, touched source | **Passed** | `Success: no issues found in 12 source files`. |
| Diff integrity | **Passed** | `git diff --check` returned clean. |

### EBS-013 Evidence

The passing EBS-013 run instantiated the actual `GatewayRuntime` through `create_configured_gateway`, actual `IntelligenceRuntime`, actual `ExecutionRuntime`, actual `LiteLLMProvider`, and the actual local schema/policy validators. It did not inject a fake provider or a hardcoded decision response. The test asserts route evidence, nonzero provider token usage, trace evidence, valid confidence, disclosed risks, capability allowlisting, dependency ordering, and a non-empty validated decision. [7]

| Required EBS-013 condition | Result |
|---|---|
| Actual real-provider call | Passed in the explicit live validation run. |
| Non-hardcoded structured decision | Passed; response originated from the configured provider and was parsed locally. |
| Schema validation | Passed. |
| Policy validation | Passed. |
| Allowlisted capabilities | Passed. |
| Dependency-valid proposed steps | Passed. |
| Risks and confidence | Passed. |
| Selection, usage, and trace evidence | Passed. |
| Capability execution | **0**. No `CapabilityRuntime` is created or called by EBS-013. |
| Workspace mutation | **0**. The benchmark supplies no workspace runtime or mutation operation. |
| Git mutation | **0**. The benchmark supplies no repository/Git runtime or mutation operation. |

## 7. Mocking Discipline

Unit tests use a controlled `FakeProvider` only at the provider transport boundary while retaining the real selection runtime, execution runtime, schema parser, policy validator, and gateway runtime. A fake `GovernedLLMGateway` consumer test returns a complete, validated `EngineeringDecisionResult`; it does not mock a raw string, `Plan`, or capability result. The EBS-013 integration test accepts no provider injection point and constructs the actual configured gateway, so a mocked provider response is not capable of satisfying the live benchmark. [7]

## 8. Remaining Limitations and Deferred Work

The following are deliberate first-milestone limits, not unaddressed scope:

| Limitation | Status |
|---|---|
| Default planner integration | Deferred. `DefaultPlanner` remains deterministic and default; no `LLMPlanner` was added. |
| Default CLI behavior | Preserved. `eag build` continues to use the G2.0 deterministic composition. |
| Multiple configured provider factories | Deferred. Initial `create_configured_gateway` supports only the approved LiteLLM transport adapter. |
| Live benchmark automation | Explicit opt-in is required to avoid unintended provider usage in ordinary local/full-suite runs. A credentialed CI integration lane remains future operational work. |
| Provider cost pricing | Depends on configured pricing catalog entries; the live result exposes usage regardless of whether an estimated cost is available. |
| Rich source analysis | The context protocol/assembler seam exists, but deeper SourceRuntime-driven evidence assembly is deferred. |
| Planner rollout/shadow mode | Deferred with G2.1 follow-on approval. |

There were no deviations that weaken the approved safety invariants. The only implementation clarification was the optional provider-schema `parameters` field noted above, which was required for strict provider-schema compatibility and remains locally policy-validated when present.

## 9. Final Status

```text
FULL_TESTS=3435 passed, 2 skipped
G2.1_TESTS=31 passed, 2 skipped
AUTONOMOUS_TESTS=150 passed
EBS_TESTS=6 passed, 1 skipped
EBS_013_STATUS=PASS (explicit live run)
RUFF=PASS (G2.1-touched files)
MYPY=PASS (12 G2.1-touched source files)

REAL_LLM_CALLS=1 verified passing EBS-013 live benchmark call
MOCKED_BOUNDARIES=Unit tests mock only the provider transport boundary; EBS-013 uses no mocked provider or decision
CAPABILITY_EXECUTIONS_DURING_EBS013=0
WORKSPACE_MUTATIONS_DURING_EBS013=0
GIT_MUTATIONS_DURING_EBS013=0

G2.1_IMPLEMENTATION=COMPLETE
EBS_013=PASS
COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
G2.2=NOT_STARTED
```

## References

[1]: ./src/eag/chief/intelligence/gateway/models.py "G2.1 immutable governed-decision models"
[2]: ./src/eag/chief/intelligence/gateway/runtime.py "G2.1 gateway selection, execution, validation, and safe-failure runtime"
[3]: ./src/eag/chief/intelligence/gateway/translator.py "G2.1 deterministic decision-to-plan translator"
[4]: ./src/eag/chief/intelligence/runtime.py "Existing IntelligenceRuntime selection ownership"
[5]: ./src/eag/chief/intelligence/execution/runtime.py "Existing ExecutionRuntime transport ownership"
[6]: ./src/eag/chief/intelligence/execution/providers/litellm_provider.py "LiteLLM provider adapter"
[7]: ./tests/test_ebs_013_governed_decision.py "EBS-013 credentialed live-provider benchmark"
