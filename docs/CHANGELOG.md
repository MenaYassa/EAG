# Changelog

All notable changes to EAG are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

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