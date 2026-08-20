# EAG G2.2 — EBS-014 Forensic Diagnosis

**Date:** 20 August 2026
**Baseline:** `98494201bec6ad684a03f89a8232331a3ae77cba` (`v2.1.0-g2.1`)
**Scope:** **Analysis only.** No source, test, fixture, acceptance-criterion, provider-configuration, commit, push, or tag change was made during this diagnosis.

> **Finding.** The deterministic repository-context pipeline supplied sufficient, correct, untruncated, relative-path-only evidence to the provider. The observed live benchmark failure occurred **inside the governed gateway before the EBS-014 grounding evaluator ran**. The exact final sub-cause—provider transport/structured-output failure, schema rejection, or deterministic policy rejection—cannot be reconstructed from the preserved run because gateway failure events and result objects intentionally retained only an aggregate failure kind/message and not the raw response, underlying validation reason, or redacted structured references.

This report distinguishes **FACT**, **INFERENCE**, and **UNKNOWN**. It does not turn a skip, a partial diagnostic success, or a deterministic satisfiability check into an EBS-014 pass.

## 1. Evidence Basis and Forensic Boundary

The recorded closeout state is `FULL_TESTS=3451 passed, 3 skipped`, `EBS_013=PASS`, `EBS_014=FAIL`, `RUFF=PASS`, and `MYPY=PASS`. The worktree remains intentionally uncommitted. A non-provider reconstruction was performed over the independent EBS-014 fixture using the same real scanner, source runtime, index runtime, graph runtime, repository-aware context assembler, request shape, and prompt renderer that the benchmark uses. It made **no provider call** and did not mutate the fixture or repository.

| Evidence item | Status | Relevance |
|---|---|---|
| Original EBS-014 benchmark/evaluator | **FACT** | Defines the live execution sequence and acceptance predicates. [1] |
| Gateway prompt and decision orchestration | **FACT** | Shows what is sent to the provider and proves that gateway failure returns before evaluator assertions. [2] |
| Decision schema/policy validator | **FACT** | Shows exact schema and provenance-rejection paths. [3] |
| Gateway event definitions | **FACT** | Shows that failure telemetry contains `kind` and attempt count but not raw response or provider-validation reason. [4] |
| Sanitized deterministic reconstruction | **FACT** | Establishes selected evidence, prompt size, fingerprints, provenance, truncation, and absence of absolute path leakage. [5] |
| Deterministic evaluator satisfiability audit | **FACT** | Proves the existing acceptance predicates can be satisfied with genuine fixture provenance. [6] |

## 2. Failed-Run Timeline

The benchmark first forms a repository-aware `EngineeringContext`, then invokes `gateway.decide(request)`. The assertion `assert result.success is True` occurs **before** any grounding-evaluator predicate is evaluated. Thus, any run with `result.success=False` fails at the gateway boundary; the reference-count evaluator did not decide that run. [1]

The original live exercise produced three categories of evidence.

| Event | Observed result | Forensic interpretation |
|---|---|---|
| Early G2.2 live attempt | OpenAI response-format rejected the then-optional `grounding_references` schema because strict schemas require all properties to appear in `required`. | **FACT:** a schema-construction defect was found and corrected before final validation. It is not sufficient evidence for the final post-fix failure. |
| Post-fix EBS-013 credentialed regression | **PASS**. | **FACT:** restoring the legacy schema preserved the established G2.1 live path. |
| Post-fix EBS-014 diagnostic call | One actual gateway diagnostic invocation returned `success=True` using the same fixture/context path. | **FACT:** the configured provider can successfully process a repository-aware request in this composition. It is not an EBS-014 acceptance pass because the complete benchmark assertions were not recorded as passing. |
| Post-fix EBS-014 full acceptance attempts | `result.success=False`, with some attempts reporting nonzero usage; the test failed at the first `result.success` assertion. | **FACT:** provider selection/execution was reached. **UNKNOWN:** whether the ultimate gateway error was `SCHEMA_INVALID`, `POLICY_REJECTED`, an execution failure, or a budget branch. No raw or typed terminal reason was preserved in the accepted forensic record. |

## 3. Complete EBS-014 Path Reconstruction

The table below reconstructs every requested stage. “Actual” means the deterministic reconstruction or preserved run evidence. It does not infer a raw provider answer that was never retained.

| # | Stage | Input | Expected output | Actual output | Pass/Fail | Evidence |
|---:|---|---|---|---|---|---|
| 1 | Repository discovery | Static fixture root | Read-only `RepositoryProfile` | Python repository; 7 files; 1 test; tests capability; VCS unavailable | **PASS** | [5] |
| 2 | Repository profile | Scanner facts and ignore rules | Relative, non-secret repository facts | `ebs_014_article_repository`, Python, no Git state access | **PASS** | [5] |
| 3 | Source analysis | Safe Python candidates | Per-file symbols/imports/locations/fingerprints | 4 analyzed source files; 9 symbols; imports including routes→service and test→routes | **PASS** | [5] |
| 4 | Indexing | Analysis results | Modules, symbols, dependencies | 4 modules, 9 symbols, 5 dependencies | **PASS** | [5] |
| 5 | Graph construction | Repository index | Dependency graph | 13 nodes, 9 edges | **PASS** | [5] |
| 6 | Candidate selection | Pagination/list endpoint goal plus index/graph | Relevant bounded files, symbols, tests, dependencies | 4 files, 9 symbols, 5 dependencies; route, service, and test all selected | **PASS** | [5] |
| 7 | Context security/redaction | Fixture paths and files | Only safe content, no absolute host paths/secrets | All selected candidates allowed; `absolute_path_leaks=false`; no protected material selected | **PASS** | [5] |
| 8 | Provenance | Selected repository facts | Stable source, index, graph, excerpt, and profile identifiers | File, symbol, dependency, excerpt, profile/state, and fingerprint provenance records are present | **PASS** | [5] |
| 9 | Snapshot/context fingerprinting | Safe content/selection projection | Deterministic fingerprints carried forward | Snapshot and context fingerprints are present and match projected metadata | **PASS** | [5] [6] |
| 10 | EngineeringContext projection | Selected bounded context | Generic `EngineeringContext` with facts, constraints, provenance, and truncation metadata | 2,860 context characters; no omissions; `truncated=false`; `insufficient=false` | **PASS** | [5] |
| 11 | Gateway request | EngineeringContext and policy | Repository-unaware governed structured request | Prompt renderer includes repository summary, findings, relevant symbols, constraints, dependencies, provenance IDs, truncation metadata, and required grounding instruction | **PASS** | [2] [5] |
| 12 | Provider response | Prompt plus strict repository-aware JSON schema | Schema-valid advisory `EngineeringDecision` with valid provenance IDs | At least one diagnostic call succeeded; final failed-run response is not retained | **UNKNOWN for final failure** | [2] [4] |
| 13 | EngineeringDecision schema/policy | Provider content | Parsed decision; allowed capabilities; nonempty valid grounding references | The final failed run did not yield `result.success=True`; exact schema/policy branch is not retained | **UNKNOWN for final failure** | [2] [3] [4] |
| 14 | Grounding evaluator | Successful `EngineeringDecision` plus selected evidence | Provenance subset plus minimum real file/symbol/test/dependency coverage | **Not reached** in failed runs because `result.success` assertion occurs first; deterministic audit proves predicates are satisfiable | **NOT REACHED / SATISFIABLE** | [1] [6] |
| 15 | Effects boundary | Context and gateway composition | No capabilities, workspace mutations, Git mutations, or shell invocations | Recorded counters are zero | **PASS** | [1] |

## 4. Provider-Visible Repository Evidence

### 4.1 Selected files, symbols, dependencies, tests, and excerpts

**FACT:** The provider-visible context contained four selected files. It included the public endpoint, the service that supplies the list, the public response-contract test, and the domain model. All were relative paths, all were present in provenance, and no selected evidence was omitted.

| Evidence type | Actual selected evidence | Selection reason | Provider-visible? |
|---|---|---|---|
| Source file | `article_app/routes.py` | `exact_goal_symbol_match` | Yes |
| Source file | `article_app/service.py` | `direct_structure` | Yes |
| Source file | `article_app/models.py` | `exact_goal_symbol_match` | Yes |
| Test file | `tests/routes_contract.py` | `exact_goal_symbol_match` | Yes |
| Key symbol | `get_articles` | `direct_structure` | Yes |
| Key symbol | `list_articles` | `direct_structure` | Yes |
| Key symbol | `test_get_articles_returns_a_list_of_article_records` | `direct_structure` | Yes |
| Dependency | `article_app.routes->article_app.service` | `direct_structure` | Yes |
| Dependency | `tests.routes_contract->article_app.routes` | `direct_structure` | Yes |
| Endpoint excerpt | `article_app/routes.py:6-11` | Exact excerpt provenance | Yes |
| Service excerpt | `article_app/service.py:7-15` | Exact excerpt provenance | Yes |
| Test excerpt | `tests/routes_contract.py:6-10` | Exact excerpt provenance | Yes |

The endpoint excerpt explicitly states that it returns a list of JSON-style records and currently has **no pagination metadata**. The service excerpt explicitly states it returns the complete list. The test excerpt asserts the list type, nonempty response, and an exact first record. Therefore, the fixture gives the provider a concrete compatibility constraint, relevant target code, a delegation relationship, and a relevant test. [5]

### 4.2 Context size, truncation, and provider rendering

| Measure | Actual | Interpretation |
|---|---:|---|
| Provider prompt characters | 7,576 | Bounded but substantial repository evidence was rendered. |
| Selected context characters | 2,860 | Well below the 24,000-character total limit. |
| Files / symbols / dependencies / excerpts | 4 / 9 / 5 / 4 | All configured selected evidence categories are populated. |
| Omitted items | 0 | No evidence was excluded by the active budget. |
| Truncated | `false` | The failure is not attributable to context-budget loss. |
| Insufficient | `false` | The selector does not classify the context as lacking relevant safe evidence. |
| Absolute path leaks | `false` | Host-path leakage is not implicated. |

**Conclusion:** **Yes, the provider received enough correct repository evidence to answer the benchmark.** The evidence contains the endpoint, response shape, service dependency, current test, all required provenance identifiers, and a clear read-only advisory constraint. There is no deterministic evidence that discovery, analysis, indexing, graph construction, selection, security, provenance, fingerprinting, or projection deprived the provider of a required fact. [5]

## 5. Context-versus-Decision Claim Audit

The user requested claim-by-claim verification for every repository-grounding claim made by the provider. This cannot be completed for the failed run because the failed run’s provider content and decision object were not retained. The gateway’s intentional redaction model captures no raw prompt/response in events, and failure events contain only a `GatewayErrorKind` and attempt count. [4]

> **Forensic limitation:** There are **zero observable provider grounding claims** from the failed EBS-014 acceptance runs. It would be unsound to invent a claim, provenance ID, file reference, symbol reference, or evaluator failure from a missing response.

| Claim field requested | Failed-run evidence | Determination |
|---|---|---|
| Provider claim | No response content retained | **UNKNOWN** |
| Provider provenance reference | No decision object retained | **UNKNOWN** |
| Reference exists in provenance | Cannot evaluate without reference | **UNKNOWN** |
| Referenced file exists | Cannot evaluate without reference | **UNKNOWN** |
| Referenced symbol exists | Cannot evaluate without reference | **UNKNOWN** |
| Claim matches selected evidence | Cannot evaluate without claim | **UNKNOWN** |
| Evidence was provider-visible | The candidate evidence listed in §4 was visible; relation to an unknown claim cannot be evaluated | **PARTIALLY FACTUAL / CLAIM MATCH UNKNOWN** |
| Fact, inference, or unsupported assertion | No retained claim | **UNKNOWN** |

The deterministic reconstruction does prove that valid structured citations *could* have been supplied, for example `file:article_app/routes.py`, `file:article_app/service.py`, `file:tests/routes_contract.py`, `symbol:get_articles`, `symbol:list_articles`, and `dependency:article_app.routes->article_app.service`. These are actual provenance IDs, not a reconstructed provider decision. [5] [6]

## 6. Grounding Evaluator Audit

The evaluator is a sequence of deterministic assertions performed only after a successful gateway result. It requires references to be a subset of actual context provenance, at least two selected files, at least two selected symbols, one selected test file, and one selected dependency. It also checks both fingerprints, nonempty decision text, assumptions, risks, and an allowlisted capability set. [1]

| Acceptance rule | Correctly implemented? | Deterministic? | Repository-grounded? | Exact-wording dependent? | Assessment |
|---|---|---|---|---|---|
| Gateway success before evaluator | Yes | Yes | N/A | No | Correct sequencing; explains why evaluator did not run on failed attempts. |
| Provenance subset | Yes | Yes | Yes | No | Strong; rejects invented IDs. |
| Two selected files | Yes | Yes | Yes | No | Appropriate minimal coverage. |
| Two selected symbols | Yes | Yes | Yes | No | Appropriate minimal structural coverage. |
| Selected test file | Yes | Yes | Yes | No | Appropriate for a compatibility-preserving change. |
| Selected dependency | Yes | Yes | Yes | No | Appropriate for route/service impact awareness. |
| Fingerprint equality | Yes | Yes | Yes | No | Correctly verifies projection continuity. |
| Narrative nonempty | Yes, but weak | Yes | No | No | Only checks content exists; it does not align individual prose claims to citations. |

**FACT:** A deterministic audit supplied valid references derived from actual selected fixture evidence and every evaluator predicate passed. The evaluator is therefore **satisfiable**, deterministic, provenance-grounded, and not dependent on exact prose wording. [6]

**INFERENCE:** The evaluator has a **semantic-claim coverage limitation**, not an observed failure defect: it validates structured citations but does not require each prose repository claim to cite a provenance ID. This limitation did not cause the recorded failure because the evaluator was not reached.

## 7. Provider Audit

| Provider-quality question | Determination | Evidence |
|---|---|---|
| Structurally valid | **UNKNOWN for failed run** | No retained provider content or typed schema error. |
| Policy valid | **UNKNOWN for failed run** | No retained decision or policy-rejection reason. |
| Repository grounded | **UNKNOWN for failed run** | No retained citations/claims; the context was adequate. |
| Incomplete / generic / hallucinated / internally inconsistent / insufficiently cited | **UNKNOWN for failed run** | The response is unavailable. |
| Can respond successfully to this context path | **FACT: yes, at least once** | A post-fix diagnostic call returned `success=True` using the same configured gateway/context composition. |

The record therefore supports neither a claim that the provider hallucinated nor a claim that it received inadequate evidence. The fair conclusion is that **provider behavior is a plausible but unproven contributor** to the final failure, while the provider’s successful diagnostic response disproves a blanket routing or context impossibility.

## 8. Benchmark Fixture and Prompt Quality

The fixture is fair for the stated objective. It isolates a small route/service/model/test structure, makes the current list response contract explicit, and contains the exact test boundary expected to change. The goal asks for pagination while preserving that contract and extending relevant tests. The prompt requires read-only advisory behavior and supplies exact provenance identifiers rather than a hardcoded answer. [1] [5]

| Quality concern | Finding |
|---|---|
| Ambiguous wording | **No material defect.** “Pagination,” “current response contract,” and “relevant tests” map to concrete fixture evidence. |
| Insufficient repository evidence | **No.** The endpoint, service, test, dependencies, excerpts, and provenance were all visible. |
| Excessive hidden assumptions | **No material defect.** The response-contract constraint and test relationship are explicit. |
| Dependence on a particular provider | **Moderate operational sensitivity, not a fixture defect.** Strict JSON/schema behavior can vary by provider execution, but assertions use evidence IDs rather than model-specific prose. |
| Brittle exact answer matching | **No.** The evaluator checks sets/intersections and general decision validity, not fixed answer text. |
| Benchmark leakage | **No.** The required references are drawn from actual selected context and are not an answer template. |
| Inadequate provenance | **No.** File, symbol, dependency, excerpt, profile/state, and fingerprint provenance is available. |

## 9. Root-Cause Classification

```text
PRIMARY_ROOT_CAUSE=The final failed EBS-014 run is not forensically classifiable beyond the G2.1 Gateway boundary because failure telemetry/result handling did not preserve the terminal typed validation reason or a redacted structured decision-reference summary. The benchmark failed at result.success before the grounding evaluator ran.

SECONDARY_ROOT_CAUSES=Provider-side variability or strict structured-output/policy nonconformance is plausible but unproven for the final failed run. An earlier strict-schema construction issue was observed and corrected; it is not established as the post-fix cause.

NOT_ROOT_CAUSES=Repository discovery; repository profile; source analysis; indexing; graph construction; candidate selection; context security/redaction; provenance generation; snapshot/context fingerprinting; EngineeringContext projection; context budget/truncation; absolute-path leakage; fixture evidence sufficiency; grounding-evaluator satisfiability; effects boundary.
```

| Classification | Result | Evidence |
|---|---|---|
| `CONTEXT_PIPELINE_DEFECT` | **NO** | Complete relevant route/service/test evidence was selected, visible, provenance-backed, untruncated, and internally fingerprint-consistent. [5] [6] |
| `GATEWAY_DEFECT` | **YES — forensic observability defect; execution root cause unknown** | On a failed response, generic failure handling returns a coarse error; events intentionally omit raw response, structured references, and typed validation reason. [2] [4] |
| `PROVIDER_BEHAVIOR` | **UNDETERMINED** | One post-fix success exists, while full acceptance attempts failed before evaluator assertions. No response record supports a more precise attribution. |
| `EVALUATOR_DEFECT` | **NO for observed failure** | It was not reached; deterministic audit proves it accepts valid real provenance. It has a non-causal semantic-claim coverage limitation. [1] [6] |
| `FIXTURE/PROMPT_DEFECT` | **NO evidence** | The provider-visible context contains all required evidence and clear constraints. [1] [5] |
| `UNKNOWN` | **Final provider/gateway terminal category and all failed-run grounding claims** | The relevant evidence was deliberately not persisted in the existing failure telemetry/result path. [2] [4] |

## 10. Exactly One Recommended Next Action

> **Recommendation F — Insufficient evidence; perform one narrowly scoped diagnostic test.**

Do **not** change implementation, evaluator, fixture/prompt, acceptance criteria, or provider configuration yet. Run **one** explicit credentialed diagnostic invocation that uses the unchanged EBS-014 fixture, context assembler, gateway request, model, schema, and policy, while capturing only the following safe forensic fields:

1. Gateway terminal `GatewayErrorKind` and stage (`execution`, `schema`, `policy`, `budget`, or success).
2. The existing context and snapshot fingerprints, selected-evidence counts, truncation state, and prompt hash.
3. If the gateway reached decision parsing, the **redacted structured** set of `grounding_references` and their existence/count intersections with selected file/symbol/test/dependency provenance; do not capture raw prose, full provider content, prompt content, secrets, or absolute host paths.
4. If schema or policy validation failed, the typed validator reason/category without provider body content.
5. Existing zero-effect counters, again proving no capability, workspace, Git, shell, commit, or push action occurred.

This single diagnostic would resolve the currently irretrievable discriminator: whether the final failure was provider execution/formatting, gateway schema/policy validation, budget enforcement, or evaluator entry. It is deliberately **not implemented or run** in this analysis task.

## 11. Hard Stop Confirmation

```text
SOURCE_MODIFICATIONS=NONE
TEST_MODIFICATIONS=NONE
BENCHMARK_CRITERIA_MODIFICATIONS=NONE
PROVIDER_CONFIGURATION_MODIFICATIONS=NONE
LIVE_PROVIDER_RETRIES_DURING_ANALYSIS=0
COMMITS=0
PUSHES=0
TAGS=0
```

## 12. Required Final Status

```text
G2.2_STATUS=OPEN
EBS_014_STATUS=FAIL
DIAGNOSIS=COMPLETE
IMPLEMENTATION_CHANGES=NONE
```

## References

[1]: tests/test_ebs_014_repository_aware_decision.py "EBS-014 benchmark, fixture composition, and grounding evaluator"
[2]: src/eag/chief/intelligence/gateway/runtime.py "Gateway execution orchestration and provider-visible prompt rendering"
[3]: src/eag/chief/intelligence/gateway/validator.py "EngineeringDecision parsing and deterministic policy validation"
[4]: src/eag/chief/intelligence/gateway/events.py "Gateway event payload and redaction boundary"
[5]: /home/ubuntu/ebs014_forensic_snapshot.json "Sanitized deterministic reconstruction of the EBS-014 pipeline and provider-visible context"
[6]: /home/ubuntu/ebs014_evaluator_audit.py "Deterministic satisfiability audit of EBS-014 acceptance predicates"
