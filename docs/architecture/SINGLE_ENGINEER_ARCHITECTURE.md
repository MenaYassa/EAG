# EAG Single-Engineer Architecture (v0.9.0)

> **Note:** Version 0.9.0 marks a historic milestone for EAG: the completion of the single‑engineer architecture.  
> Up to this point, EAG was designed to function as an autonomous engineer capable of solving engineering tasks end to end on its own.  
> Starting with Sprint 8, the project will evolve from *"an autonomous engineer"* into *"an autonomous engineering organization."*  
> This document captures the complete architectural state at the precise moment this milestone was achieved.  

---

## 1. The Complete Architecture Diagram

The architecture is best understood as an **orchestration flow** – data and control move through a series of specialised components, with feedback loops that keep the system's mental model synchronised with reality.

```
User (CLI · API · Open WebUI)
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              EAG Kernel                                  │
│   EventBus · RuntimeContext · DependencyInjection · ToolRegistry         │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            Chief Runtime                                 │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ Goal Intelligence · Capability Runtime · Model Router            │    │
│  │ Execution Orchestrator · Reflection · Review                     │    │
│  │ Health Monitoring · Benchmark Integration                        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              Planner                                     │
│  ┌─────────────────────────────────────────────────────────────-─────┐   │
│  │ Dependency‑aware planning · Execution ordering                    │   │
│  │ Capability selection · Simulation · Approval                      │   │
│  │ Task graph generation                                             │   │
│  └─────────────────────────────────────────────────────────────────-─┘   │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Capability Platform                             │
│  ┌─────────────┐ ┌───────────────┐ ┌──────────────────┐ ┌─────────────┐  │
│  │  Workspace  │ │  Repository   │ │ Transformation   │ │   Review    │  │
│  │ Capability  │ │ Capability    │ │ Capability       │ │ Capability  │  │
│  └─────────────┘ └───────────────┘ └──────────────────┘ └─────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                      Composite Capability                        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Execution Runtime                                │
│   Sessions · Changesets · Transactional Edits · Rollback                 │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Safety Runtime                                 │
│   Approval Gates · Risk Classification · Guardrails                      │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  Knowledge & Source Intelligence Platform                │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────────┐   │
│  │ Repository │ │  Source  │ │  Index   │ │         Graph            │   │
│  │  Runtime   │ │ Runtime  │ │ Runtime  │ │         Runtime          │   │
│  └────────────┘ └──────────┘ └──────────┘ └──────────────────────────┘   │
│       Git,           Parsing,     Cross‑file   Impact Analysis,          │
│    Profiles,        AST,        Resolution,   Explainability,            │
│    Frameworks       Symbols     Semantic      Dependency Tracing         │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Reflection Loop                                 │
│  ┌─────────────┐  ┌───────────────┐  ┌──────────────────────────────┐    │
│  │   Review    │  │  Benchmark    │  │    Knowledge Refresh         │    │
│  │   Runtime   │  │   Runtime     │  │   (incremental re‑indexing)  │    │
│  └─────────────┘  └───────────────┘  └──────────────────────────────┘    │
│         ▲                                                                │
│         └────────────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────────┘
```

The arrows indicate the primary flow of a task, but the Reflection Loop feeds back into Knowledge, ensuring the system's understanding remains current after every execution.

---

## 2. Every Platform (Kernel → Benchmark)

### 2.1 Kernel Platform (Sprint 1)
The central nervous system of EAG. It manages dependency injection, the shared `RuntimeContext`, and the `EventBus` that coordinates all asynchronous communication between runtimes. It also hosts the `ToolRegistry` for extending capabilities without breaking core logic.

### 2.2 Chief Runtime (Sprint 7)
The brain of the operation. The Chief orchestrates the entire process:
- **Goal Intelligence** – interprets user intent and breaks it into high‑level objectives.
- **Capability Runtime** – manages the lifecycle of available capabilities.
- **Model Router** – selects the appropriate LLM (OpenAI, Anthropic, etc.) for the current subtask via LiteLLM integration.
- **Execution Orchestrator** – coordinates the sequence of steps, delegating to the Planner and later to Execution.
- **Reflection** – evaluates outcomes and feeds insights back into the system.
- **Review** – performs post‑execution quality checks.
- **Health Monitoring** – tracks system performance and resource usage.
- **Benchmark Integration** – interfaces with the benchmark suite for continuous validation.

### 2.3 Planner (Sprint 5)
Bridging knowledge and execution, the Planner decomposes high‑level goals into step‑by‑step plans. Its responsibilities now include:
- **Dependency‑aware planning** – respects orderings and prerequisites.
- **Execution ordering** – determines the optimal sequence of tasks.
- **Capability selection** – chooses which capabilities (Workspace, Repository, etc.) are needed for each step.
- **Simulation** – performs dry‑runs to foresee impact.
- **Approval** – submits plans for human or automated approval.
- **Task graph generation** – produces a structured graph of tasks for execution.

### 2.4 Capability Platform (Sprint 7.6)
This is where the Chief's decisions are translated into concrete actions. The platform consists of:
- **Workspace Capability** – handles file system operations, project scaffolding, and workspace management.
- **Repository Capability** – interacts with version control (git), profiles, and framework detection.
- **Transformation Capability** – applies AST‑based mutations, semantic edits, and structural diffs.
- **Review Capability** – performs quality gates, style checks, and test execution.
- **Composite Capability** – composes multiple capabilities into a single high‑level operation.

### 2.5 Execution Runtime (Sprint 2 & 6)
Executes the approved plan with transactional semantics. It manages sessions, changesets, and supports rollback on failure, ensuring that the system can recover gracefully from errors.

### 2.6 Safety Runtime (Sprint 3)
Acts as a firewall, classifying operations as safe, risky, or destructive, and enforcing human approval gates for critical changes. It is tightly integrated with the Planner and Execution Runtime.

### 2.7 Knowledge & Source Intelligence Platform (Sprint 4)
Transforms raw code into structured knowledge:
- **Repository Runtime** – profiles the codebase, discovers frameworks, entry points, and directory structures.
- **Source Runtime** – parses ASTs, extracts symbols (functions, classes), and builds call graphs.
- **Index Runtime** – resolves cross‑file imports to build a global semantic index.
- **Graph Runtime** – constructs the Engineering Graph, running algorithms like `impact`, `why`, and `path` to trace dependencies and evaluate consequences.

### 2.8 Reflection Loop (Sprint 7)
After execution, the system does not consider the task complete until it has validated the outcome:
- **Review Runtime** – runs static checks, linters, and unit tests.
- **Benchmark Runtime** – executes the relevant benchmarks (EBS‑0 suite) to confirm correctness.
- **Knowledge Refresh** – incrementally re‑indexes the repository, ensuring the system's mental model remains perfectly synchronised with the file system.

### 2.9 EBS‑0 Benchmark Platform (v0.91)
The evaluation framework ensures the single‑engineer architecture functions cohesively. The benchmark suite now consists of **real engineering tasks** that EAG must solve end‑to‑end:

- **EBS‑001 – CLI Calculator**  
  Build a command‑line calculator that handles basic arithmetic, with proper argument parsing and error handling.

- **EBS‑002 – File Organizer**  
  Automatically organise a messy directory by file type, date, or custom rules, with support for dry‑run and undo.

- **EBS‑003 – Notes CLI**  
  Create a note‑taking tool with persistent storage, search, and tagging – testing both CRUD and search capabilities.

- **EBS‑004 – FastAPI CRUD**  
  Generate a fully functional REST API with FastAPI, including models, endpoints, and database integration.

- **EBS‑005 – TODO App**  
  Build a full‑featured TODO application with a React frontend and a backend API, testing cross‑file refactoring and frontend/backend coordination.

These benchmarks prove that EAG can safely and correctly plan, execute, and validate changes across a wide range of real‑world scenarios.

---

## 3. The Execution Pipeline

EAG strictly enforces a separation between facts (knowledge), reasoning (planning), and execution (action). The pipeline now includes a formal reflection stage.

1. **Observation (Knowledge Gathering):**  
   - The `RepositoryRuntime` scans the project.  
   - The `SourceRuntime` parses files into ASTs and extracts symbols.  
   - The `IndexRuntime` and `GraphRuntime` connect these symbols into a dependency graph.  

2. **Reasoning (Planning & Orchestration):**  
   - The user issues a goal.  
   - The **Chief Runtime** routes the request, interprets the goal, and delegates to the **Planner**.  
   - The Planner queries the Engineering Graph, performs dependency‑aware planning, selects appropriate capabilities, and generates a task graph.  

3. **Validation:**  
   - The plan is run through the `SafetyRuntime` – risky/destructive actions halt the pipeline for human approval.  
   - A dry‑run simulates the outcome, and the plan is approved.  

4. **Execution:**  
   - The `ExecutionRuntime` applies the approved changesets using transactional semantics (supporting rollback on failure).  

5. **Reflection:**  
   - Upon completion, the `ReviewRuntime` performs quality checks, and the `BenchmarkRuntime` executes relevant benchmarks.  
   - An `ExecutionCompleted` event triggers the `KnowledgeRefresh` to incrementally re‑index the repository, ensuring the system's mental model remains perfectly synchronised with the file system.  

---

## 4. The Capability Model

EAG's capability model is structured around tool delegation and model‑agnostic execution:

- **Capability Runtime** – manages the lifecycle of capabilities, including registration, discovery, and invocation.  
- **Capability Registry** – a central store (part of the Kernel) where all capabilities are registered with their metadata (inputs, outputs, risk level).  
- **Workspace Capability** – file operations, scaffolding, directory management.  
- **Repository Capability** – git operations, framework detection, profiling.  
- **Transformation Capability** – AST mutations, semantic edits, structural diffing.  
- **Review Capability** – linting, testing, style enforcement.  
- **Composite Capability** – composes multiple atomic capabilities into a single high‑level operation (e.g., "refactor a class" might involve reading, transforming, and testing).  

**Agnostic Routing:** Models (OpenAI, Anthropic, etc.) are treated as interchangeable reasoning engines via LiteLLM integration.

**Dynamic Tool Selection:** Tools are registered in the Kernel's `ToolRegistry`. The Chief selects only the relevant tools for each subtask, minimising context bloat.

**Explainability by Default:** Every capability (like the Graph's `why` or `impact` tools) is designed to produce auditable, human‑readable explanations of its reasoning.

---

## 5. Engineering Philosophy

EAG intentionally separates engineering into independent concerns, each with clear boundaries:

- **Knowledge** – Repository, Source, Index, Graph – how the system understands the codebase.
- **Reasoning** – Goal Intelligence, Planning – how the system decides what to do.
- **Execution** – Capabilities, Workspace – how the system applies changes.
- **Validation** – Review, Benchmark – how the system verifies correctness.
- **Intelligence** – LLMs through model‑agnostic routing – the external reasoning engine.

This separation allows any layer to evolve independently without requiring changes to the others. It also makes the system auditable, testable, and extensible – a foundation that will carry EAG into the multi‑engineer era.

---

## 6. The Roadmap Snapshot

The following sprints led to the v0.9.0 milestone:

- **Sprint 0** – Foundation & project setup  
- **Sprint 1** – Kernel (EventBus, DI, RuntimeContext)  
- **Sprint 2** – Execution Runtime (sessions, changesets)  
- **Sprint 3** – Repository & Safety (profiling, guardrails)  
- **Sprint 4** – Source Intelligence (AST, symbols, graph)  
- **Sprint 5** – Planning (decomposition, simulation, approval)  
- **Sprint 6** – Engineering Platform (transformations, AST mutations)  
- **Sprint 7** – Chief Engineer (orchestration, routing, reflection)  
- **v0.9.0** – **Single Engineer Architecture** ✅  

*(The v0.91 release added the EBS‑0 Benchmark Platform to validate the architecture.)*

---

## 7. What's Next

The completion of Sprint 7 marks the end of the single‑engineer architecture.

Future work shifts from increasing the capability of one engineer to coordinating many engineers.

**Sprint 8 introduces:**
- Worker Runtime – distributes tasks across multiple workers.
- Parallel execution – runs independent subtasks concurrently.
- Conflict resolution – handles overlapping changes from different workers.
- Distributed planning – plans that span multiple repositories or services.

**Sprint 9 introduces:**
- Autonomous engineering loops – the system learns from past executions.
- Self‑improvement – improves its own planning and execution strategies.
- Organisational learning – shares knowledge across teams and projects.

---

*This document was frozen on the day v0.9.0 was declared complete – a moment when EAG proved itself as a capable, autonomous, single software engineer.*
