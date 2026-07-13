# EAG Roadmap

* * *

## Completed Sprints

### Sprint 0 — Foundation ✅

*   Foundation documents
    
*   Repository bootstrap
    
*   Project skeleton
    

### Sprint 1 — Kernel & Plugin Platform ✅

*   Kernel implementation
    
*   EventBus
    
*   RuntimeContext
    
*   Dependency injection container
    
*   Tool Registry
    
*   Plugin loading and validation
    
*   Plugin manifest schema
    

### Sprint 2 — Execution Platform ✅

*   Execution Runtime
    
*   Session management
    
*   Changesets
    
*   File change tracking
    
*   Execution result reporting
    
*   Session lifecycle (create, suspend, resume, complete)
    

### Sprint 3 — Safety & Engineering Runtime ✅

*   Safety Runtime
    
*   Operation classification (Safe, Risky, Destructive)
    
*   Human approval gates
    
*   Audit trail
    
*   Repository Runtime
    
*   Repository scanning
    
*   Framework detection
    
*   Directory classification
    
*   Repository Profile model
    

### Sprint 4 — Engineering Knowledge Platform ✅

*   Source Runtime
    
*   Symbol extraction
    
*   Import tracking
    
*   Call graph extraction per file
    
*   Engineering Index
    
*   Cross-file symbol resolution
    
*   Relationship tracking
    
*   Incremental index updates
    
*   Engineering Graph
    
*   Graph construction from index
    
*   Graph metrics (centrality, cycles, clusters)
    
*   Impact analysis algorithm
    
*   Explainability ("why") algorithm
    
*   Pathfinding algorithm
    

* * *

## Upcoming Sprints

### Sprint 5 — Planner Engine 🔜

*   Goal decomposition
    
*   Planning models (Plan, PlanTask, ValidationResult)
    
*   Execution plan generation
    
*   Plan validation against Safety Runtime
    
*   Dry-run capability (simulate without side effects)
    
*   Human approval workflow
    
*   Planner CLI integration
    

**Target Version:** v0.7

### Sprint 6 — Chief Engineer

*   LiteLLM integration
    
*   Model-agnostic routing
    
*   Model selection based on task type
    
*   Tool selection from Tool Registry
    
*   Multi-model coordination
    
*   Chief Engineer CLI integration
    

**Target Version:** v0.9

### Sprint 7 — Workers

*   Worker agent runtime
    
*   Parallel execution of independent tasks
    
*   Worker collaboration protocol
    
*   Conflict detection and resolution
    
*   Progress reporting and coordination
    
*   Worker lifecycle management
    

**Target Version:** v1.0

* * *

## Version Goals

| Version | Name | Status |
| --- | --- | --- |
| v0.1 | Foundation | ✅ Complete |
| v0.2 | Kernel & Plugins | ✅ Complete |
| v0.3 | Safety & Execution | ✅ Complete |
| v0.4 | Repository & Source Intelligence | ✅ Complete |
| v0.5 | Engineering Graph Platform | ✅ Complete |
| v0.7 | Planner Engine | 🔜 Sprint 5 |
| v0.9 | Chief Engineer | Sprint 6 |
| v1.0 | Autonomous Engineering Platform | Sprint 7 |

* * *

## Post-1.0 Vision

After v1.0, EAG will evolve toward:

*   **Multi-repository coordination** — Understand and reason across multiple repositories
    
*   **Infrastructure Management** — Manage deployment targets, environments, and configurations
    
*   **Documentation Automation** — Generate and maintain documentation from engineering knowledge
    
*   **Plugin SDK** — First-class plugin development toolkit with templates and testing harness
    
*   **Knowledge Graph Persistence** — Store engineering graphs for long-term, cross-session knowledge
    
*   **Team Coordination** — Multiple EAG instances collaborating on engineering work
    

* * *

## Sprint Progress

```
v0.1 Foundation             ████████████████████ 100%
v0.2 Kernel & Plugins       ████████████████████ 100%
v0.3 Safety & Execution     ████████████████████ 100%
v0.4 Repo & Source          ████████████████████ 100%
v0.5 Engineering Graph      ████████████████████ 100%
v0.7 Planner                ░░░░░░░░░░░░░░░░░░░░   0%
v0.9 Chief                  ░░░░░░░░░░░░░░░░░░░░   0%
v1.0 Autonomous             ░░░░░░░░░░░░░░░░░░░░   0%
```

* * *

## Guiding Principles for Roadmap Planning

1.  **Architecture before implementation** — Every sprint begins with a design document
    
2.  **Knowledge before action** — EAG must understand before it acts
    
3.  **Safety scales with capability** — Every new capability must pass through the Safety Runtime
    
4.  **Documentation evolves with implementation** — Each sprint updates all relevant docs
    
5.  **Always leave the project better than it was found** — Each sprint improves architecture, tests, and documentation