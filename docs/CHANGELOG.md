# Changelog

All notable changes to EAG are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

* * *

## Published Gen2 Governed Evidence Boundaries — G2.4.14 through G2.4.21

### Published milestones

| Milestone | Tag | Published boundary |
| --- | --- | --- |
| G2.4.14 | `v2.4.14-g2.4.14` | Artifact readiness evidence validation. |
| G2.4.15 | `v2.4.15-g2.4.15` | Governed artifact promotion eligibility evidence. |
| G2.4.16 | `v2.4.16-g2.4.16` | Human external-transition authorization evidence. |
| G2.4.17 | `v2.4.17-g2.4.17` | Sole durable, fail-closed pre-execution external-transition control ledger. |
| G2.4.18 | `v2.4.18-g2.4.18` | Immutable destination-contract evidence boundary, strengthened with typed exact request/assessment provenance. |
| G2.4.19 | `v2.4.19-g2.4.19` | Immutable outcome-semantics policy evidence boundary, with typed exact request/assessment provenance and outcome-unknown safety. |
| G2.4.20 | `v2.4.20-g2.4.20` | Declared destination-contract attestation-policy evidence only; no trust, issuer authentication, signature verification, destination truth, or execution readiness. |
| G2.4.21 | `v2.4.21-g2.4.21` (original) | Immutable local construction work-order evidence binding exact upstream evidence, custody/composition declarations, intent digests, capabilities, limits, identity, and expiry. |
| G2.4.21 provenance remediation | `v2.4.21-provenance.1` | Follow-up typed immutable `assessed_request_id`/`assessed_request_digest` linkage for construction-work-order assessments, closing request/assessment substitution without inferring provenance from generic evidence references. |

G2.4.18 was published at commit `2606a1060f7341d269d5dfee5575c7a0d7050adb`. G2.4.19 was published at commit `429f1ecf4782b1ce8f925c58a517b547999fb325`. G2.4.20 was published at commit `2749185ac44e38e86e4d1971a654ba26252e93a2`. The original G2.4.21 milestone was published at commit `e8931c5dc196d25a4741447d5b4580a7f84ead4d` under unchanged tag `v2.4.21-g2.4.21`. The accepted G2.4.21 typed request/assessment provenance remediation was subsequently published at commit `55c9d02e698558bbf7f68773207c3c80b9995b3d` under immutable follow-up tag `v2.4.21-provenance.1`, with `REMOTE_VERIFICATION=PASS`. The G2.4.19 deterministic acceptance record is:

```text
EBS_034=PASS
EBS_034_COMPLETENESS=PASS
EXACT_UPSTREAM_BINDING=PASS
POLICY_ID_SELF_IDENTITY=PASS
OUTCOME_UNKNOWN_SAFETY=PASS
FAIL_CLOSED_BEHAVIOR=PASS
NO_EXECUTION_AUTHORITY=PASS
G2_4_17_SEPARATION=PASS
```

These are immutable evidence, deterministic/static validation, and capability-absence results. G2.4.17 remains the sole durable pre-execution control ledger for its existing external-artifact-transition profile; G2.4.18 remains destination-contract evidence only; G2.4.19 remains outcome-semantics policy evidence only; G2.4.20 remains declared attestation-policy evidence only; and G2.4.21 remains construction work-order evidence only. The typed provenance remediation across G2.4.18–G2.4.21 closed request/assessment substitution gaps through exact immutable ID/digest linkage, not generic evidence-reference inference.

The published chain is artifact readiness → promotion eligibility → external transition authorization → external transition control ledger → external destination contract evidence → external outcome-semantics policy evidence → declared attestation-policy evidence → construction work-order evidence. Neither G2.4.21 nor its provenance remediation creates or leases workspaces, writes files, runs commands, installs dependencies, invokes runtimes, accesses credentials/network, builds/tests applications, performs correction, retry, rollback, recovery, reconciliation, publication, release, or deployment. `G2.4.22=NOT_STARTED` for implementation; its design/authorization stage is separate and remains unimplemented.

The evidence classifications remain truthful: `OBSERVED_ZERO_EFFECT_CATEGORIES=NONE`; operational categories are `CAPABILITY_ABSENT`; and immutable evidence, policy, request, result, and test-owned state are established through `DIRECT_STATE_PROOF`.

* * *


## v0.91.0 — Chief Engineer & Benchmarking

### Added
* Chief Engineer Runtime and Execution Orchestrator
* Model Router, Capability Discovery, and Tool Selection
* EBS-0 Benchmark Platform with 5 benchmarks (EBS-001 through EBS-005)
* Single-engineer architecture completion

### Notes
This release marks a significant milestone as we complete the single-engineer architecture with Sprint 7 and introduce our initial benchmark suite. EAG is now capable of end-to-end task execution and validation. We are preparing to evolve into an autonomous engineering organization starting with Sprint 8 (Workers).

* * *


## v0.8.0 — Engineering Platform

### Added
* Semantic Transformations and AST mutation system
* Transactional edits with rollbacks
* Git and File changesets integrated with Safety Runtime
* Structural Diff engine
* `CompositeEdit` handling

### Notes
This release merges previous discrete tasks into a complete engineering and transformation framework (Sprint 6). The application can now safely execute semantic operations.

* * *
## v0.7.0 — Planner Engine

### Added

*   Planner Runtime

*   Goal decomposition and analysis

*   Execution plan generation

*   Plan Simulator for dry-run capabilities (simulate without side effects)

*   Plan validation engine

*   Human Approval engine and workflow

*   Planner CLI integration

*   Strategy registry (e.g., SequentialStrategy)


### Changed

*   Updated `EventBus` to support planner-related events (`PlanningStarted`, `PlanGenerated`, etc.)

*   EAG CLI enhanced with `planner` capabilities


### Notes

This release completes the Planner Engine. EAG can now decompose goals, simulate changes without side effects, run validation, request human approval for risky operations, and generate structured execution plans.

* * *

## v0.5 — Engineering Graph Platform

### Added

*   Engineering Graph Runtime
    
*   Graph construction from Engineering Index
    
*   Graph node and edge models
    
*   Relationship types: Calls, Imports, Inherits, References, Contains
    
*   Impact analysis algorithm — determines all symbols affected by a change
    
*   Explainability ("why") algorithm — produces human-readable explanations for any symbol
    
*   Pathfinding algorithm — finds shortest dependency path between two symbols
    
*   Centrality metrics — identifies critical symbols in the repository
    
*   Cycle detection — identifies circular dependencies
    
*   Cluster detection — identifies tightly-coupled symbol groups
    
*   `eag graph` CLI command
    
*   `eag impact <symbol>` CLI command
    
*   `eag why <symbol>` CLI command
    
*   `eag path <a> <b>` CLI command
    
*   GraphNode, GraphEdge, ImpactResult, ExplainabilityResult, PathResult models
    

### Changed

*   EngineeringIndex model extended with relationship tracking
    
*   SourceAnalysis model extended with call graph edges
    
*   EventBus now supports `GraphUpdated` event
    
*   RuntimeContext now holds Engineering Graph reference
    

### Notes

This release completes the Engineering Knowledge Platform. EAG can now  
construct a full directed graph of engineering relationships from source  
files and answer questions about impact, dependency, and explainability.  
The platform is ready for Sprint 5 — the Planner Engine.

* * *

## v0.4 — Repository & Source Intelligence

### Added

*   Repository Runtime
    
*   Repository scanning and directory walking
    
*   Language detection
    
*   Framework detection
    
*   Entry point identification
    
*   Configuration and manifest file detection
    
*   Repository Profile model
    
*   Source Runtime
    
*   Symbol extraction (functions, classes, methods, variables)
    
*   Import tracking and resolution
    
*   Export tracking
    
*   Per-file call graph extraction
    
*   Symbol visibility classification (Public, Private, Internal)
    
*   Engineering Index Runtime
    
*   Cross-file symbol resolution
    
*   Relationship aggregation (imports, calls, inherits, references)
    
*   Incremental index updates
    
*   `eag scan` CLI command
    
*   `eag symbols <file>` CLI command
    
*   `eag index` CLI command
    
*   RepositoryProfile, SourceAnalysis, Symbol, Import, EngineeringIndex models
    

### Changed

*   EventBus now supports `RepositoryScanned`, `SymbolsExtracted`, `IndexUpdated` events
    
*   RuntimeContext now holds Repository Profile and Engineering Index references
    
*   Plugin manifest schema updated to support source parser plugins
    

### Notes

This release transforms EAG from a runtime platform into a knowledge  
platform. EAG can now understand repositories at the symbol level and  
build a cross-file index of engineering relationships.

* * *

## v0.3 — Safety & Execution Platform

### Added

*   Safety Runtime
    
*   Operation classification: Safe, Risky, Destructive
    
*   Human approval gates for destructive actions
    
*   Audit trail logging
    
*   Safety violation detection and blocking
    
*   Execution Runtime
    
*   Session management (create, suspend, resume, complete)
    
*   Changeset model (additions, modifications, deletions)
    
*   File change tracking with diffs
    
*   Execution result reporting
    
*   Safety integration with Execution Runtime
    
*   Session, Changeset, FileChange, SafetyDecision, ExecutionResult models
    

### Changed

*   EventBus now supports `SafetyViolation`, `ExecutionStarted`, `ExecutionCompleted` events
    
*   RuntimeContext now holds active session state
    
*   Kernel startup sequence updated to initialize Safety Runtime before Execution Runtime
    

### Notes

This release makes EAG safe to operate. Every execution passes through  
safety gates, and destructive actions require human approval. The audit  
trail ensures every action is explainable.

* * *

## v0.2 — Kernel & Plugin Platform

### Added

*   Kernel implementation
    
*   EventBus — internal pub/sub system
    
*   RuntimeContext — shared state container
    
*   Dependency injection container
    
*   Tool Registry
    
*   Plugin loading at startup
    
*   Plugin manifest schema and validation
    
*   Plugin interface contract
    
*   Event log for replay and debugging
    
*   Dead-letter queue for failed event processing
    
*   EventBus, RuntimeContext, ToolRegistry, Plugin models
    

### Notes

This release establishes the core platform. The Kernel, EventBus, and  
Tool Registry provide the foundation for all future runtimes. Plugins can  
now be loaded, validated, and registered with the Tool Registry.

* * *

## v0.0.1 — Foundation

### Added

*   Project vision
    
*   Constitution
    
*   Initial architecture
    
*   Roadmap
    
*   Contribution guide
    
*   Repository foundation
    

### Notes

This release contains no production code. It establishes the  
architectural and philosophical foundation of EAG.