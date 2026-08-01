# EAG Single-Engineer Architecture (v0.91)

> **Note:** Version 0.9.0/0.91 represents a historic milestone for EAG: the completion of the single-engineer architecture.
> Up to this point, EAG was designed to function as an autonomous engineer capable of solving engineering tasks end to end on its own.
> Starting with Sprint 8, the project will evolve from "an autonomous engineer" into "an autonomous engineering organization."
> This document captures the complete architectural state at the precise moment this milestone was achieved.

* * *

## 1. The Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User / Interface                              │
│                        CLI · API · Open WebUI                           │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                          EAG Kernel                                     │
│      EventBus · RuntimeContext · DependencyInjection · ToolRegistry     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                       Chief Engineer (Sprint 7)                         │
│           Model Router · Execution Orchestrator · Tool Selector         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                         Planner (Sprint 5)                              │
│       Goal Analysis · Task Decomposition · Simulation · Approval        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                       Execution Runtime (Sprint 2 & 6)                  │
│             Sessions · Changesets · Transactional Edits                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                        Safety Runtime (Sprint 3)                        │
│             Approval Gates · Risk Classification · Guardrails           │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                 Knowledge & Source Intelligence Platform                │
│                                                                         │
│   ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ ┌──────────┐   │
│   │   Repository   │ │     Source     │ │   Index      │ │  Graph   │   │
│   │   Runtime      │ │     Runtime    │ │   Runtime    │ │ Runtime  │   │
│   │   (Sprint 4)   │ │    (Sprint 4)  │ │  (Sprint 4)  │ │(Sprint 4)│   │
│   └───────┬────────┘ └───────┬────────┘ └──────┬───────┘ └────┬─────┘   │
│           │                  │                 │              │         │
│     Git, Profiles     Parsing, AST      Cross-file    Impact Analysis,  │
│     Frameworks        Extract Symbols   Resolution    Explainability    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                 EBS-0 Benchmark Platform (v0.91)                        │
│                 End-to-end evaluation & validation                      │
└─────────────────────────────────────────────────────────────────────────┘
```

* * *

## 2. Every Platform (Kernel → Benchmark)

### 2.1 Kernel Platform (Sprint 1)
The central nervous system of EAG. It manages dependency injection, the shared `RuntimeContext`, and the `EventBus` that coordinates all asynchronous communication between runtimes. It also hosts the `ToolRegistry` for extending capabilities without breaking core logic.

### 2.2 Runtime Platform (Sprint 2)
Handles the fundamental execution loop, including `ExecutionRuntime` and `SessionRuntime`. It defines the lifecycle of a task from planning through execution, applying changesets safely and transactionally.

### 2.3 Repository & Safety Platform (Sprint 3)
The `RepositoryRuntime` profiles the codebase, discovering frameworks, entry points, and directory structures. The `SafetyRuntime` acts as a firewall, classifying operations as safe, risky, or destructive, enforcing human approval gates for critical changes.

### 2.4 Source Intelligence Platform (Sprint 4)
Transforms raw code into structured knowledge.
*   **Source Runtime:** Parses ASTs, extracts symbols (functions, classes), and builds call graphs.
*   **Index Runtime:** Resolves cross-file imports to build a global semantic index.
*   **Graph Runtime:** Constructs the Engineering Graph, running algorithms like `impact`, `why`, and `path` to trace dependencies and evaluate the consequences of changes.

### 2.5 Planner Platform (Sprint 5)
Bridging knowledge and execution, the Planner decomposes high-level goals into step-by-step plans. It validates changes against the Safety Runtime, performs dry-runs (simulations), and seeks approval before submitting a finalized plan for execution.

### 2.6 Engineering Platform (Sprint 6)
Focuses on actual transformation capabilities. It includes semantic transformations, AST-based mutation, transactional edits with rollbacks, structural diffing, and composite edit handling. It gives EAG hands to mold the codebase securely.

### 2.7 Chief Engineer (Sprint 7)
The brain of the operation. It orchestrates the entire process, utilizing a Model Router to select the appropriate LLM for the task. It delegates tasks, selects tools contextually, and manages the execution loop and memory. It makes decisions dynamically.

### 2.8 EBS-0 Benchmark Platform (v0.91)
The evaluation framework. It ensures the single-engineer architecture functions cohesively by testing the system against a standardized suite of tasks, verifying that EAG can safely and correctly plan, execute, and rollback changes.

* * *

## 3. The Execution Pipeline

EAG strictly enforces a separation between facts (knowledge), reasoning (planning), and execution (action).

1.  **Observation (Knowledge Gathering):**
    *   The `RepositoryRuntime` scans the project.
    *   The `SourceRuntime` parses files into ASTs and extracts symbols.
    *   The `IndexRuntime` and `GraphRuntime` connect these symbols into a dependency graph.
2.  **Reasoning (Planning & Orchestration):**
    *   The user issues a goal.
    *   The **Chief Engineer** routes the request and delegates to the **Planner**.
    *   The Planner queries the Engineering Graph to assess impact and generates a series of `PlanTask`s (changesets).
3.  **Validation:**
    *   The plan is run through the `SafetyRuntime`. Risky/destructive actions halt the pipeline for human approval. A dry-run simulates the outcome.
4.  **Execution:**
    *   The `ExecutionRuntime` applies the approved changesets using transactional semantics (supporting rollback on failure).
5.  **Reflection:**
    *   Upon completion, an `ExecutionCompleted` event triggers the Knowledge Platform to incrementally re-index the repository, ensuring the system's mental model remains perfectly synchronized with the file system.

* * *

## 4. The Capability Model

EAG's capability model is structured around tool delegation and model-agnostic execution:
*   **Agnostic Routing:** Models (OpenAI, Anthropic, etc.) are treated as interchangeable reasoning engines via LiteLLM integration.
*   **Dynamic Tool Selection:** Tools are registered in the Kernel's `ToolRegistry`. The Chief Engineer selects only the relevant tools (e.g., semantic search, AST mutation, grep) required for the current sub-task, minimizing context bloat.
*   **Explainability by Default:** Every capability (like the Graph's `why` or `impact` tools) is designed to produce auditable, human-readable explanations of its reasoning.

* * *

## 5. The Benchmark Suite (EBS-0)

To validate the completion of the single-engineer architecture, the EBS-0 Benchmark Platform introduces a suite of 5 core benchmarks. These benchmarks prove EAG can solve problems reliably end-to-end:

*   **EBS-001:** Validates basic goal comprehension and safe file modification.
*   **EBS-002:** Tests the Source Intelligence Platform by requiring cross-file refactoring and import resolution.
*   **EBS-003:** Challenges the Planner and Safety Runtimes with risky transformations requiring simulated dry-runs and rollback recovery.
*   **EBS-004:** Evaluates the Chief Engineer's ability to orchestrate multi-step complex tasks dynamically selecting tools.
*   **EBS-005:** Assesses the Engineering Graph's impact analysis capabilities when dealing with circular dependencies and deep call graphs.

*(With the passing of EBS-001 through EBS-005, EAG has proven itself as a capable, autonomous, single software engineer.)*