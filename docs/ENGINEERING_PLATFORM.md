# EAG Engineering Platform Guide

> A complete walkthrough of every subsystem in EAG, from the Kernel to  
> the Engineering Graph. This document is the architectural map for any  
> new contributor — read this once, and you will understand how EAG works.

* * *

## Platform Overview

EAG is an engineering operating system. It transforms raw source code into  
structured engineering knowledge, reasons about that knowledge, and  
executes changes safely.
The platform is organized as a pipeline:

```
Kernel
    │
    ├── EventBus
    ├── RuntimeContext
    │
    ├── Execution Runtime ──── Safety Runtime
    │
    ├── Repository Runtime
    ├── Source Runtime
    ├── Index Runtime
    ├── Graph Runtime
    │
    └── Tool Registry ──── Plugins
```

Every subsystem coordinates through EventBus events. No subsystem calls  
another directly. The Kernel owns lifecycle; the RuntimeContext owns shared  
state; each Runtime owns its domain.

* * *

## 1. Kernel

The Kernel is the root of the system. It is the first to start and the  
last to shut down.

### Responsibilities

*   Initialize all runtime services in dependency order
    
*   Provide the dependency injection container
    
*   Hold the RuntimeContext (shared state)
    
*   Manage the Tool Registry
    
*   Coordinate graceful shutdown
    

### Startup Sequence

1.  EventBus created
    
2.  Tool Registry created
    
3.  RuntimeContext created and given EventBus + Tool Registry
    
4.  Safety Runtime started (must be before Execution)
    
5.  Repository Runtime started
    
6.  Source Runtime started
    
7.  Index Runtime started
    
8.  Graph Runtime started
    
9.  Execution Runtime started (depends on Safety)
    
10.  RuntimeContext registers all runtimes
     
11.  Platform ready
     

### Shutdown Sequence

1.  Execution Runtime stopped
    
2.  Graph Runtime stopped
    
3.  Index Runtime stopped
    
4.  Source Runtime stopped
    
5.  Repository Runtime stopped
    
6.  Safety Runtime stopped
    
7.  RuntimeContext cleared
    
8.  EventBus destroyed
    
9.  Platform stopped
    

* * *

## 2. EventBus

The EventBus is the communication backbone. All runtimes communicate  
exclusively through events.

### Event Lifecycle

```
Runtime A emits event
    │
    ▼
EventBus receives event
    │
    ▼
EventBus routes event to all subscribers
    │
    ▼
Each subscriber processes event
    │
    ├─► Success: ACK
    ├─► Retry (up to 3 attempts)
    └─► Failure: Dead-letter queue
```

### Event Catalog

| Event | Emitted By | Subscribed By | Trigger |
| --- | --- | --- | --- |
| `RepositoryScanned` | RepositoryRuntime | SourceRuntime | Repository scan complete |
| `SymbolsExtracted` | SourceRuntime | IndexRuntime | Source analysis complete for a file |
| `IndexUpdated` | IndexRuntime | GraphRuntime | Index rebuilt or incrementally updated |
| `GraphUpdated` | GraphRuntime | ExecutionRuntime | Graph construction or update complete |
| `ExecutionStarted` | ExecutionRuntime | SafetyRuntime | A session begins execution |
| `SafetyViolation` | SafetyRuntime | ExecutionRuntime | A destructive action was attempted without approval |
| `ExecutionCompleted` | ExecutionRuntime | IndexRuntime | Session finished — triggers re-index if files changed |

* * *

## 3. RuntimeContext

The RuntimeContext is the shared state container. It lives inside the  
Kernel and is accessible to all runtimes through dependency injection.

### Contents

```
RuntimeContext:
    event_bus: EventBus
    tool_registry: ToolRegistry
    repository_profile: RepositoryProfile | None
    engineering_index: EngineeringIndex | None
    engineering_graph: EngineeringGraph | None
    active_session: Session | None
    runtimes: dict[str, Runtime]
```

The RuntimeContext is the _only_ place where cross-runtime state is  
stored. Runtimes read from and write to the context, but never to each  
other.

* * *

## 4. Repository Runtime

**What it does:** Scans a repository and produces a structured profile.

### Input

```
root_path: str (path to the repository)
```

### Process

1.  Walk the directory tree
    
2.  Skip ignored paths (`.git`, `node_modules`, `__pycache__`, etc.)
    
3.  Identify languages by file extension and content analysis
    
4.  Detect frameworks by looking for known config files and imports
    
5.  Identify entry points (main.py, index.js, app.py, etc.)
    
6.  Classify directories (source, test, config, docs, vendor)
    
7.  Find configuration and manifest files
    

### Output

```
RepositoryProfile:
    root_path: str
    languages: list[str]              # ["Python", "TypeScript"]
    frameworks: list[str]             # ["FastAPI", "React"]
    entry_points: list[str]           # ["src/main.py", "src/index.tsx"]
    directory_structure: DirectoryNode
        path: str
        children: list[DirectoryNode]
        classification: Source | Test | Config | Docs | Vendor
    config_files: list[str]           # ["pyproject.toml", ".eslintrc.json"]
    manifest_files: list[str]         # ["package.json", "requirements.txt"]
```

### Emits

*   `RepositoryScanned(repository_profile)`
    

* * *

## 5. Source Runtime

**What it does:** Parses source files and extracts symbols, imports, and  
call graphs.

### Input

```
file_path: str
language: str (from RepositoryProfile)
```

### Process

1.  Read the file
    
2.  Select the appropriate parser based on language
    
3.  Parse the file into an AST or equivalent structure
    
4.  Extract symbols (functions, classes, methods, variables)
    
5.  Extract imports and exports
    
6.  Build a per-file call graph
    
7.  Classify symbol visibility (public, private, internal)
    

### Output

```
SourceAnalysis:
    file_path: str
    symbols: list[Symbol]
        name: str
        qualified_name: str
        kind: Function | Class | Method | Variable | Module
        visibility: Public | Private | Internal
        line_start: int
        line_end: int
        signature: str | None
    imports: list[Import]
        source: str              # module or file path
        symbols: list[str]       # imported names
        line: int
    exports: list[str]
    call_graph: list[CallEdge]
        caller: str              # qualified name
        callee: str              # qualified name or expression
        line: int
```

### Emits

*   `SymbolsExtracted(file_path, source_analysis)`
    

* * *

## 6. Index Runtime

**What it does:** Aggregates source analyses into a cross-file index of  
symbols and relationships.

### Input

```
source_analyses: list[SourceAnalysis] (from SourceRuntime)
```

### Process

1.  Collect all symbols across all files
    
2.  Resolve imports to actual symbol definitions (cross-file)
    
3.  Build lookup table: qualified_name → SymbolEntry
    
4.  Track relationships: which symbols import, call, or reference which
    
5.  Identify unresolved references (external dependencies)
    
6.  Build file-level summary statistics
    

### Output

```
EngineeringIndex:
    symbols: dict[str, SymbolEntry]
        qualified_name: str (key)
        file_path: str
        line: int
        kind: Function | Class | Method | Variable | Module
        visibility: Public | Private | Internal
    relationships: list[Relationship]
        source: str              # qualified name
        target: str              # qualified name
        type: Imports | Calls | Inherits | References
    file_index: dict[str, FileEntry]
        path: str
        language: str
        symbol_count: int
        import_count: int
    unresolved: list[UnresolvedReference]
        symbol: str
        source_file: str
        line: int
        possible_target: str | None
```

### Emits

*   `IndexUpdated(engineering_index)`
    

* * *

## 7. Graph Runtime

**What it does:** Constructs a directed graph from the Engineering Index  
and provides algorithms for impact analysis, explainability, and  
pathfinding.

### Input

```
engineering_index: EngineeringIndex
```

### Process

1.  Create a node for every symbol in the index
    
2.  Create an edge for every relationship
    
3.  Compute graph metrics (centrality, clusters, cycles)
    
4.  Index the graph for fast lookups
    
5.  Prepare algorithm entry points
    

### Output

```
EngineeringGraph:
    nodes: dict[str, GraphNode]
        id: str (qualified name, key)
        kind: Function | Class | Method | Variable | Module
        file_path: str
        visibility: Public | Private | Internal
        attributes: dict[str, any]
    edges: list[GraphEdge]
        source: str (node id)
        target: str (node id)
        type: Calls | Imports | Inherits | References | Contains
        weight: float
```

### Algorithms

#### Impact Analysis

```
ImpactResult:
    direct: list[str]          # symbols that directly depend on this one
    transitive: list[str]      # all symbols transitively affected
    files_affected: list[str]  # all files containing affected symbols
    severity: Low | Medium | High | Critical
    explanation: str           # human-readable summary
```

**Algorithm:** Reverse BFS from the target symbol through all edges. The  
number of layers and the number of affected symbols determine severity.

#### Explainability (Why)

```
ExplainabilityResult:
    symbol: SymbolEntry
    purpose: str               # inferred from context and naming
    depends_on: list[str]      # symbols this depends on
    depended_by: list[str]     # symbols that depend on this
    centrality_score: float
    explanation: str           # full prose explanation
```

**Algorithm:** Combine forward and reverse dependency traversal with  
centrality scoring. Produce a natural-language explanation of the symbol's  
role.

#### Pathfinding

```
PathResult:
    found: bool
    path: list[str]            # ordered list of symbol ids
    edge_types: list[str]      # type of each edge
    total_weight: float
    explanation: str           # human-readable path description
```

**Algorithm:** Dijkstra's algorithm with edge weights. Return the shortest  
path and a human-readable explanation of the dependency chain.

#### Centrality

```
centrality() → dict[str, float]
```

**Algorithm:** Betweenness centrality. Identifies symbols that, if  
removed, would most disrupt the dependency graph.

#### Cycle Detection

```
cycles() → list[list[str]]
```

**Algorithm:** Tarjan's strongly connected components. Each SCC of size > 1  
is a cycle. Returns all detected cycles as ordered lists of symbol ids.

### Emits

*   `GraphUpdated(engineering_graph)`
    

* * *

## 8. Safety Runtime

**What it does:** Classifies all operations and enforces guardrails.

### Classification

| Classification | Meaning | Action |
| --- | --- | --- |
| Safe | Read-only, additive, or non-destructive | Proceed automatically |
| Risky | Modifies existing files or state | Warn user, request confirmation |
| Destructive | Deletes files, overwrites state, or irreversibly changes the repository | Require explicit human approval |

### Process

1.  Receive an operation request
    
2.  Analyze the operation type and target
    
3.  Classify the operation
    
4.  If Safe → approve immediately
    
5.  If Risky → emit warning, request confirmation
    
6.  If Destructive → block, request explicit human approval
    
7.  Record the decision in the audit trail
    
8.  Return SafetyDecision
    

### Output

```
SafetyDecision:
    operation_id: str
    classification: Safe | Risky | Destructive
    requires_approval: bool
    approval_granted: bool | None
    reason: str
    approver: str | None
    timestamp: str
```

### Emits

*   `SafetyViolation(operation_id, reason)` — when a destructive action is attempted without approval
    

* * *

## 9. Execution Runtime

**What it does:** Manages engineering tasks from creation to completion.

### Session Lifecycle

```
Pending → Planning → Approved → Executing → Completed
       → Rejected
       → Failed → RolledBack
```

### Process

1.  Create a session with a goal
    
2.  Build a changeset (planned modifications)
    
3.  Submit each FileChange to Safety Runtime for classification
    
4.  If all Safe → proceed
    
5.  If any Risky → request user confirmation
    
6.  If any Destructive → require human approval
    
7.  Apply approved changes
    
8.  Report results
    
9.  Emit `ExecutionCompleted` → triggers IndexRuntime re-index
    

### Output

```
ExecutionResult:
    session_id: str
    changeset: Changeset
        additions: list[FileChange]
        modifications: list[FileChange]
        deletions: list[FileChange]
    status: Pending | Approved | Applied | Failed | RolledBack
    safety_decision: SafetyDecision
    results: list[ActionResult]
        file_path: str
        status: Success | Failed
        error: str | None
```

### Emits

*   `ExecutionStarted(session_id, changeset)`
    
*   `ExecutionCompleted(session_id, execution_result)`
    

* * *

## 10. Tool Registry & Plugins

### Tool Registry

The Tool Registry is the plugin extension point. Plugins register tools,  
and the platform can discover and invoke them.

```
ToolRegistry:
    tools: dict[str, Tool]
        name: str
        description: str
        handler: Callable
        parameters: Schema
```

### Plugin Lifecycle

1.  Plugin discovered at startup
    
2.  Plugin manifest validated
    
3.  Plugin loaded into memory
    
4.  `Plugin.init(context)` called
    
5.  `Plugin.register(tool_registry)` called
    
6.  Tools available to platform
    

### Plugin Constraints

*   The core **never** depends on plugins
    
*   Plugins **can** subscribe to EventBus events
    
*   Plugins **can** provide tools, parsers, or providers
    
*   Removing a plugin **must not** break any core functionality
    
*   Plugins are loaded at startup and validated against a manifest schema
    

* * *

## 11. Planner (Sprint 5 — Future)

The Planner sits above the Knowledge Platform and below the Execution  
Platform. It transforms goals into validated, approved execution plans.

```
Goal
    │
    ├── Decompose into sub-tasks
    ├── Query Engineering Graph for relevant symbols
    ├── Generate changeset for each task
    ├── Validate against Safety Runtime
    ├── Dry-run (simulate, no side effects)
    ├── Request human approval (if destructive)
    └── Submit to Execution Runtime
```

### Planning Models

```
Plan:
    id: str
    goal: str
    tasks: list[PlanTask]
    validation: ValidationResult
    approval: ApprovalRecord | None
    status: Draft | Validated | Approved | Rejected | Executing | Done

PlanTask:
    id: str
    description: str
    target_symbols: list[str]
    changeset: Changeset
    dependencies: list[str]  # task ids this depends on
```

* * *

## 12. Chief Engineer (Sprint 6 — Future)

The Chief Engineer routes tasks to models and selects tools.

```
Plan Task
    │
    ├── Analyze task type
    ├── Select best model for task type
    ├── Select relevant tools from Tool Registry
    ├── Delegate to model with tools
    └── Collect result
```

* * *

## 13. Workers (Sprint 7 — Future)

Workers execute tasks in parallel with coordination.

```
Plan
    │
    ├── Identify independent tasks
    ├── Spawn workers for parallel tasks
    ├── Coordinate dependent tasks (wait for predecessors)
    ├── Detect conflicts between parallel changes
    ├── Resolve conflicts or escalate
    └── Merge results
```

* * *

## Full Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                      USER GOAL                          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Repository Runtime                     │
│      Scan repository → Repository Profile              │
│      Event: RepositoryScanned                          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Source Runtime                       │
│      Parse files → Symbols, Imports, Call Graphs       │
│      Event: SymbolsExtracted                           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Index Runtime                        │
│      Aggregate → Cross-file Symbol Resolved Index      │
│      Event: IndexUpdated                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Graph Runtime                        │
│      Build graph → Engineering Graph                   │
│      Algorithms: Impact, Why, Path, Centrality, Cycles │
│      Event: GraphUpdated                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Planner (Sprint 5)                      │
│      Goal → Decompose → Plan → Validate → Dry Run      │
│      → Approve                                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Chief Engineer (Sprint 6)                  │
│      Route tasks to models, select tools               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                Workers (Sprint 7)                       │
│      Execute tasks in parallel with coordination       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Safety Runtime                         │
│      Classify → Approve / Block / Warn                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                Execution Runtime                        │
│      Apply changes → Report results                    │
│      Event: ExecutionCompleted                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Index Runtime (re-index)                   │
│      Update index and graph with new state             │
└─────────────────────────────────────────────────────────┘
```

* * *

## Cognitive Model

EAG operates as a cognitive system with three layers:
| Layer | Question | Components | State |
| --- | --- | --- | --- |
| Facts | What is the repository? | Repository, Source, Index, Graph Runtimes | Immutable, persistent |
| Reasoning | What should change? | Graph Algorithms, Planner, Chief | Transient, auditable |
| Execution | How to change? | Safety, Execution Runtimes | Controlled, gated |

This separation ensures that engineering knowledge is always reliable,  
reasoning is always auditable, and execution is always safe.