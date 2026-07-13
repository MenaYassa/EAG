# EAG Architecture v0.5

* * *

## Executive Summary

EAG is a model-agnostic engineering operating system. It is built as a  
layered platform where each layer has a single responsibility and coordinates  
with other layers through a central EventBus. The architecture enforces  
separation of facts, reasoning, and execution.
At the core is the Kernel, which manages lifecycle, dependency injection,  
and the Runtime Context. Around the Kernel are runtime services — each  
responsible for one capability: repository scanning, source analysis,  
indexing, graph construction, safety checks, and execution. Plugins extend  
the platform through the Tool Registry without the core ever depending on them.

* * *

## Engineering Philosophy

| Principle | Meaning |
| --- | --- |
| Separation of concerns | Facts, reasoning, and execution are independent |
| Runtime owns lifecycle | Each runtime controls its own startup, shutdown, and state |
| Models are immutable | Data structures are never mutated in place |
| Builders build | Builders construct objects; they do not reason |
| Algorithms reason | Algorithms analyze, score, and explain; they do not execute |
| Services support | Services provide infrastructure: I/O, persistence, coordination |
| Events coordinate | Runtimes communicate through EventBus, never through direct calls |
| Core never depends on plugins | The plugin boundary is one-directional |
| Knowledge is permanent | Once discovered, engineering knowledge is never lost |
| Every action is explainable | No operation occurs without an audit trail |

* * *

## Layered Architecture

```
┌─────────────────────────────────────────────────┐
│               Presentation Layer                │
│            CLI · API · Open WebUI               │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│                 Kernel                          │
│ EventBus · RuntimeContext · DependencyInjection │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│             Runtime Services                    │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│ │   Safety │ │ Execution│ │Repository│          │
│ │  Runtime │ │ Runtime  │ │ Runtime  │          │
│ └──────────┘ └──────────┘ └──────────┘          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│ │ Source   │ │ Index    │ │ Graph    │          │
│ │ Runtime  │ │ Runtime  │ │ Runtime  │          │
│ └──────────┘ └──────────┘ └──────────┘          │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│            Knowledge Platform                   │
│      Repository Profile · Source Analysis       │
│      Engineering Index · Engineering Graph      │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│            Execution Platform                   │
│      Sessions · Changesets · Safety Gates       │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│               Plugin Layer                      │
│        Tool Registry · Providers · Extensions   │
└─────────────────────────────────────────────────┘
```

* * *

## Runtime Services

### EventBus

The EventBus is the nervous system of EAG. All runtime services  
communicate exclusively through events. No runtime calls another runtime  
directly.
**Responsibilities:**

*   Publish events when state changes
    
*   Subscribe to events from other runtimes
    
*   Route events to the correct subscribers
    
*   Maintain an ordered event log for replay and debugging
    

**Key Events:**
| Event | Emitted By | Consumed By |
| --- | --- | --- |
| `RepositoryScanned` | RepositoryRuntime | SourceRuntime, IndexRuntime |
| `SymbolsExtracted` | SourceRuntime | IndexRuntime |
| `IndexUpdated` | IndexRuntime | GraphRuntime |
| `GraphUpdated` | GraphRuntime | ExecutionRuntime, SafetyRuntime |
| `SafetyViolation` | SafetyRuntime | ExecutionRuntime |
| `ExecutionStarted` | ExecutionRuntime | SafetyRuntime |
| `ExecutionCompleted` | ExecutionRuntime | IndexRuntime (re-index) |

### Kernel

The Kernel is the central coordinator. It is the first component to start  
and the last to shut down.
**Responsibilities:**

*   Initialize and manage all runtime services
    
*   Provide dependency injection for all components
    
*   Hold the Runtime Context (shared state container)
    
*   Handle graceful startup and shutdown sequences
    
*   Register and manage the Tool Registry
    

### RuntimeContext

The Runtime Context is the shared state container that lives within the  
Kernel. It holds references to all active runtimes, the EventBus, the Tool  
Registry, and the current session state.

```
RuntimeContext:
    event_bus: EventBus
    tool_registry: ToolRegistry
    active_session: Session | None
    repository_profile: RepositoryProfile | None
    engineering_index: EngineeringIndex | None
    engineering_graph: EngineeringGraph | None
```

### RepositoryRuntime

Scans a repository and produces a Repository Profile — a structured  
description of the project.
**Responsibilities:**

*   Walk the repository tree
    
*   Detect languages and frameworks
    
*   Identify entry points, configuration files, and manifests
    
*   Classify directories (source, test, config, docs)
    
*   Produce a Repository Profile model
    

**Output:** `RepositoryProfile` — an immutable model containing:

```
RepositoryProfile:
    root_path: str
    languages: list[str]
    frameworks: list[str]
    entry_points: list[str]
    directory_structure: DirectoryNode
    config_files: list[str]
    manifest_files: list[str]
```

**Emits:** `RepositoryScanned`

### SourceRuntime

Analyzes individual source files to extract symbols, imports, and  
structural information.
**Responsibilities:**

*   Parse source files using language-appropriate parsers
    
*   Extract symbols (functions, classes, methods, variables)
    
*   Track imports and exports
    
*   Build call graphs per file
    
*   Identify symbol visibility (public, private, internal)
    

**Output:** `SourceAnalysis` — an immutable model containing:

```
SourceAnalysis:
    file_path: str
    symbols: list[Symbol]
        name: str
        kind: str
        visibility: str
        line_start: int
        line_end: int
        signature: str
    imports: list[Import]
        source: str
        symbols_imported: list[str]
        line: int
    exports: list[str]
    call_graph: list[CallEdge]
        caller: str
        callee: str
        line: int
```

**Emits:** `SymbolsExtracted`

### IndexRuntime

Builds and maintains a semantic index of all discovered symbols, files,  
and relationships across the repository.
**Responsibilities:**

*   Aggregate SourceAnalysis results from all files
    
*   Resolve imports to actual symbol definitions
    
*   Build a lookup index: symbol name → definition location
    
*   Track cross-file relationships
    
*   Maintain index freshness (incremental updates)
    

**Output:** `EngineeringIndex` — an immutable model containing:

```
EngineeringIndex:
    symbols: dict[str, SymbolEntry]
        qualified_name: str
        file_path: str
        line: int
        kind: str
        visibility: str
    relationships: list[Relationship]
        source_symbol: str
        target_symbol: str
        type: str  (imports, calls, inherits, references)
    file_index: dict[str, FileEntry]
        path: str
        language: str
        symbol_count: int
        import_count: int
    unresolved: list[UnresolvedReference]
```

**Emits:** `IndexUpdated`

### GraphRuntime

Constructs the Engineering Graph from the Engineering Index. This is the  
crown jewel of the Knowledge Platform.
**Responsibilities:**

*   Build a directed graph from index relationships
    
*   Compute graph metrics (centrality, clusters, cycles)
    
*   Run impact analysis algorithms
    
*   Provide explainability queries
    
*   Find dependency paths between symbols
    

**Output:** `EngineeringGraph` — an immutable model containing:

```
EngineeringGraph:
    nodes: dict[str, GraphNode]
        symbol_id: str
        kind: str
        file_path: str
        attributes: dict[str, any]
    edges: list[GraphEdge]
        source: str
        target: str
        type: str
        weight: float
    algorithms: GraphAlgorithms
        impact(symbol) → ImpactResult
        why(symbol) → ExplainabilityResult
        path(a, b) → PathResult
        centrality() → dict[str, float]
        cycles() → list[list[str]]
```

**Emits:** `GraphUpdated`

### SafetyRuntime

Enforces safety guardrails on all operations, especially those that modify  
files or state.
**Responsibilities:**

*   Classify operations: safe, risky, destructive
    
*   Require human approval for destructive actions
    
*   Maintain an audit trail of all operations
    
*   Detect and block unauthorized changes
    
*   Emit safety violation events
    

**Output:** `SafetyDecision` — an immutable model containing:

```
SafetyDecision:
    operation_id: str
    classification: Safe | Risky | Destructive
    requires_approval: bool
    approval_granted: bool | None
    reason: str
    timestamp: str
```

**Emits:** `SafetyViolation` (when a destructive action is attempted without approval)

### ExecutionRuntime

Manages the lifecycle of engineering tasks — from creation to completion.
**Responsibilities:**

*   Create and manage execution sessions
    
*   Track changesets (planned and applied)
    
*   Coordinate with SafetyRuntime before applying changes
    
*   Execute approved changes
    
*   Report execution results
    
*   Trigger re-indexing after successful execution
    

**Output:** `ExecutionResult` — an immutable model containing:

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
```

**Emits:** `ExecutionStarted`, `ExecutionCompleted`

* * *

## Knowledge Platform

The Knowledge Platform is the combination of Repository Runtime, Source  
Runtime, Index Runtime, and Graph Runtime. Together, they transform raw  
source files into structured engineering knowledge.

### Knowledge Flow

```
Repository (raw files)
    │
    ▼
RepositoryRuntime
    │
    ▼
RepositoryProfile (structure, languages, frameworks)
    │
    ▼
SourceRuntime
    │
    ▼
SourceAnalysis (symbols, imports, call graphs per file)
    │
    ▼
IndexRuntime
    │
    ▼
EngineeringIndex (cross-file resolved symbols and relationships)
    │
    ▼
GraphRuntime
    │
    ▼
EngineeringGraph (directed graph with metrics, impact, explainability)
    │
    ▼
Planner (Sprint 5 — future)
```

### Engineering Graph

The Engineering Graph is the central knowledge artifact of EAG. It is a  
directed graph where:

#### Nodes

Each node represents a symbol in the repository:

```
GraphNode:
    id: str (qualified name)
    kind: Function | Class | Method | Variable | Module
    file_path: str
    line_range: (int, int)
    visibility: Public | Private | Internal
    attributes: dict[str, any]
```

#### Edges

Each edge represents a relationship between symbols:

```
GraphEdge:
    source: str (node id)
    target: str (node id)
    type: Calls | Imports | Inherits | References | Contains
    weight: float
    metadata: dict[str, any]
```

#### Algorithms

The GraphRuntime exposes the following algorithms:
| Algorithm | Input | Output | Description |
| --- | --- | --- | --- |
| `impact(symbol)` | Symbol id | `ImpactResult` | All symbols affected if this symbol changes — computed via reverse dependency traversal |
| `why(symbol)` | Symbol id | `ExplainabilityResult` | Human-readable explanation of why this symbol exists, what depends on it, and what it depends on |
| `path(a, b)` | Two symbol ids | `PathResult` | Shortest dependency path between two symbols |
| `centrality()` | — | `dict[str, float]` | Betweenness centrality for all nodes — identifies critical symbols |
| `cycles()` | — | `list[list[str]]` | Detects circular dependencies |
| `cluster(symbol)` | Symbol id | `ClusterResult` | Identifies the tightly-coupled cluster around a symbol |

#### Impact Analysis

Impact analysis answers the question: _"If I change this symbol, what else  
breaks?"_

```
ImpactResult:
    direct: list[str]       # symbols that directly depend on this
    transitive: list[str]   # all symbols transitively affected
    files_affected: list[str]
    severity: Low | Medium | High | Critical
    explanation: str        # human-readable summary
```

#### Explainability (Why)

The `why` algorithm produces a human-readable explanation of a symbol's  
role in the repository:

```
ExplainabilityResult:
    symbol: SymbolEntry
    purpose: str                # inferred purpose from context
    depends_on: list[str]       # what this symbol depends on
    depended_by: list[str]      # what depends on this symbol
    centrality_score: float
    explanation: str            # full prose explanation
```

#### Path Finding

Path finding traces the dependency chain between two symbols:

```
PathResult:
    found: bool
    path: list[str]         # ordered list of symbol ids
    edge_types: list[str]   # type of each edge in the path
    total_weight: float
    explanation: str        # human-readable path description
```

* * *

## Execution Platform

The Execution Platform manages how changes are planned, validated, and  
applied.

### Sessions

An execution session represents a unit of work:

```
Session:
    id: str
    goal: str
    changeset: Changeset
    status: Pending | Planning | Approved | Executing | Completed | Failed
    safety_decisions: list[SafetyDecision]
    created_at: str
    updated_at: str
```

### Changesets

A changeset describes a set of planned modifications:

```
Changeset:
    additions: list[FileChange]
    modifications: list[FileChange]
    deletions: list[FileChange]

FileChange:
    file_path: str
    diff: str
    reason: str
    safety_class: Safe | Risky | Destructive
```

### Safety Gates

Before any changeset is applied:

1.  SafetyRuntime classifies each `FileChange`
    
2.  If any change is `Destructive`, human approval is required
    
3.  If any change is `Risky`, a warning is issued and confirmation is requested
    
4.  If all changes are `Safe`, the changeset may proceed
    
5.  The audit trail records the decision and the approver (if applicable)
    

* * *

## Event System

### Event Flow

```
User Goal
    │
    ▼
RepositoryRuntime ──► EventBus ──► SourceRuntime
    │
    ▼
EventBus ──► IndexRuntime
    │
    ▼
EventBus ──► GraphRuntime
    │
    ▼
EventBus ──► ExecutionRuntime
    │
    ▼
EventBus ──► SafetyRuntime
    │
    ▼
EventBus ──► ExecutionRuntime
    │
    ▼
Apply Changes
    │
    ▼
EventBus ──► IndexRuntime (re-index)
```

### Event Ordering

Events are processed in order. The EventBus maintains a sequential log. If  
a runtime fails to process an event, it is retried up to three times  
before being placed in a dead-letter queue for manual inspection.

* * *

## Dependency Injection

The Kernel provides a dependency injection container for all runtimes.

```python
# Simplified example
class Kernel:
    def __init__(self):
        self.event_bus = EventBus()
        self.tool_registry = ToolRegistry()
        self.context = RuntimeContext()

    def start(self):
        # Order matters: dependencies must start first
        self.safety_runtime = SafetyRuntime(self.event_bus, self.context)
        self.repo_runtime = RepositoryRuntime(self.event_bus, self.context)
        self.source_runtime = SourceRuntime(self.event_bus, self.context)
        self.index_runtime = IndexRuntime(self.event_bus, self.context)
        self.graph_runtime = GraphRuntime(self.event_bus, self.context)
        self.execution_runtime = ExecutionRuntime(
            self.event_bus, self.context, self.safety_runtime
        )

        # Register all runtimes in context
        self.context.register("safety", self.safety_runtime)
        self.context.register("repository", self.repo_runtime)
        self.context.register("source", self.source_runtime)
        self.context.register("index", self.index_runtime)
        self.context.register("graph", self.graph_runtime)
        self.context.register("execution", self.execution_runtime)
```

Each runtime receives only what it needs. No runtime has access to the  
Kernel itself — only to the EventBus and the RuntimeContext.

* * *

## Plugin Architecture

Plugins extend EAG through the Tool Registry. A plugin registers one or  
more tools that can be invoked by the Execution Runtime or made available  
to future planning and agent layers.

```python
# Plugin interface (simplified)
class Plugin:
    name: str
    version: str

    def register(self, tool_registry: ToolRegistry) -> None:
        """Register tools with the Tool Registry."""
        ...

    def init(self, context: RuntimeContext) -> None:
        """Initialize plugin with access to runtime context."""
        ...
```

### Plugin Constraints

*   Plugins cannot modify the Kernel or emit to the EventBus directly
    
*   Plugins can subscribe to events through the Tool Registry
    
*   Plugins can provide new tools, parsers, or providers
    
*   The core never depends on plugins — removing a plugin must never break EAG
    
*   Plugins are loaded at startup and validated against a manifest schema
    

* * *

## Planning Architecture (Sprint 5 — Future)

The Planner Engine will sit above the Knowledge Platform and below the  
Execution Platform. It will transform engineering goals into validated,  
approved execution plans.

```
Goal
    │
    ▼
Planner
    ├── Decompose goal into sub-tasks
    ├── Query Engineering Graph for relevant symbols
    ├── Generate execution plan
    ├── Validate plan against Safety Runtime
    ├── Dry-run plan (simulate, no side effects)
    ├── Request human approval (if destructive)
    └── Submit to Execution Runtime
```

### Planning Models

```
Plan:
    id: str
    goal: str
    tasks: list[PlanTask]
        description: str
        target_symbols: list[str]
        changeset: Changeset
        dependencies: list[str]  # task ids this depends on
    validation: ValidationResult
    approval: ApprovalRecord | None
    status: Draft | Validated | Approved | Rejected | Executing | Done
```

### Planner Workflow

1.  **Decompose** — Break the goal into atomic, ordered tasks
    
2.  **Graph Query** — For each task, query the Engineering Graph for relevant symbols, impact analysis, and dependency paths
    
3.  **Generate** — Produce a changeset for each task
    
4.  **Validate** — Check everything against safety rules and graph consistency
    
5.  **Dry Run** — Simulate execution without side effects; report what would happen
    
6.  **Approval** — If any task is destructive or risky, request human approval
    
7.  **Execute** — Submit approved plan to Execution Runtime
    

* * *

## Departments

EAG's organizational structure mirrors its architecture:
| Department | Responsibility | Current Runtime(s) |
| --- | --- | --- |
| Executive | Goal management, planning (future) | Planner (Sprint 5) |
| Knowledge | Repository understanding | Repository, Source, Index, Graph |
| Planning | Task decomposition, plan validation | Planner (Sprint 5) |
| Engineering | Execution of changes | Execution Runtime |
| Infrastructure | Runtime lifecycle, DI, plugins | Kernel, EventBus, Tool Registry |
| Security | Safety, guardrails, approvals | Safety Runtime |
| Documentation | README, architecture docs, changelog | (documentation set) |
| Data | Models, immutability, serialization | All immutable models |

* * *

## Future Evolution

| Version | Capability | Milestone |
| --- | --- | --- |
| v0.5 | Engineering Graph Platform | ✅ Complete |
| v0.7 | Planner Engine | Sprint 5 |
| v0.9 | Chief Engineer — model routing, tool selection | Sprint 6 |
| v1.0 | Autonomous Engineering Platform — workers, parallel execution | Sprint 7 |

* * *

## Data Flow Summary

```
Goal → Planner → Tool Selection → Execution → Observation → Knowledge Update → Report
```

This data flow, defined in v0.1, remains the guiding principle. The  
difference is that every stage is now backed by a concrete runtime service.