# EAG Roadmap v2

## Architecture at a Glance

```
User
↓
Chief Engineer ← Orchestrates tasks, selects tools, plans execution
↓
Workers ← Execute independent tasks in parallel
↓
Engineering Platforms
├── Planner ← Goal decomposition, validation, simulation, approval
├── Execution ← Runtime, sessions, changesets, metrics
├── Workspace ← File system, project context, environment
├── Repository ← Git, scanning, profiles, safety
├── Source ← Parsing, indexing, cross‑file resolution, graph
└── Transformations ← Edits, refactorings, semantic operations
```

---

## Completed Sprints

### Sprint 0 — Foundation ✅

- Foundation documents
- Repository bootstrap
- Project skeleton

---

### Sprint 1 — Kernel Platform ✅

- Kernel implementation
- EventBus
- RuntimeContext
- Dependency injection container
- Tool Registry
- Plugin loading and validation
- Plugin manifest schema

---

### Sprint 2 — Runtime Platform ✅

Instead of only Execution Runtime, this sprint now covers:

- Execution Runtime
- Session Runtime
- Runtime Context
- Execution Lifecycle
- Metrics
- Events
- Health

---

### Sprint 3 — Safety & Repository Platform ✅

Repository and Safety merged into one platform:

- Repository Runtime
- Git Runtime
- Transactions
- Repository Profiles
- Framework Detection
- Safety Runtime
- Approval Gates
- Audit

---

### Sprint 4 — Source Intelligence Platform ✅

This sprint grew substantially beyond the original scope:

- Source Runtime
- Engineering Models
- Language Providers
- Python Analyzer
- Engineering Index
- Cross‑file Resolution
- Repository Explorer
- Engineering Graph
- Impact Analysis
- Semantic Search
- Explainability
- Incremental Updates

---

### Sprint 5 — Planner Platform ✅

This sprint now deserves its own detailed breakdown. It was implemented as a series of sub‑sprints:

- **5.1** Planning Models
- **5.2** Strategy Framework
- **5.3** Intelligence Pipeline
- **5.4** Operations Library
- **5.5** Validation Platform
- **5.6** Simulation Platform
- **5.7** Approval Engine
- **5.8** Planner CLI

**Outcome:**
Goal Analysis · Task Decomposition · Execution Plans · Validation · Simulation · Approval · Planning Intelligence · Planner CLI

**Target Version:** v0.7 ✅

---

### Sprint 6 — Engineering Platform ✅

This is a major shift from the original "Chief Engineer" sprint. It focuses on building the execution, workspace, repository, source, and transformation platforms that support the Chief Engineer.

**Sub‑sprints:**

- **6.1** Execution Platform
- **6.2** Runtime Platform
- **6.3** Workspace Platform
- **6.4** Repository Platform
- **6.5** Source & Transformation Platform
  - **6.5A** Engineering Models
  - **6.5B** Transformation Framework
  - **6.5C** Semantic Rename
  - **6.5D** Transformation Platform
  - **6.5E** Transformation Library
- **6.6** Production Readiness

**Target Version:** v0.8 ✅

---

### Sprint 7 — Chief Engineer ✅

This sprint turns the Chief Engineer into an orchestrator.

- Chief Engineer Runtime
- LiteLLM Integration
- Model Router
- Capability Discovery
- Transformation Selection
- Tool Selection
- Execution Orchestrator
- Context Manager
- Review Loop
- Engineering Memory
- Chief CLI

**Target Version:** v0.9 ✅

---

### EBS-0 Benchmark Platform ✅

- Benchmarking Framework
- EBS-001
- EBS-002
- EBS-003
- EBS-004
- EBS-005

**Target Version:** v0.91 ✅

---

## Upcoming Sprints

### Sprint 8 — Workers ⏳

Workers become a full‑fledged distributed execution system.

- Worker Runtime
- Worker Registry
- Task Distribution
- Parallel Execution
- Conflict Resolution
- Supervisor
- Aggregation
- Scaling

**Target Version:** v1.0

---

### Sprint 9 — Autonomous Engineering 🔜

Evolving from an autonomous engineer to an autonomous engineering organization.

- Organization orchestration
- Advanced multi-agent workflows
- High-level project planning and execution

**Target Version:** v1.1

---

## Version Roadmap

| Version | Milestone                       | Status |
| ------- | ------------------------------- | ------ |
| v0.1    | Foundation                      | ✅     |
| v0.2    | Kernel Platform                 | ✅     |
| v0.3    | Runtime & Safety                | ✅     |
| v0.4    | Repository Platform             | ✅     |
| v0.5    | Source Intelligence             | ✅     |
| v0.6    | Engineering Platform            | ✅     |
| v0.7    | Planning Intelligence           | ✅     |
| v0.8    | Semantic Transformations        | ✅     |
| v0.9    | Chief Engineer                  | ✅     |
| v0.91   | EBS-0 Benchmark Platform        | ✅     |
| v1.0    | Autonomous Multi‑Agent Workers  | ⏳     |
| v1.1    | Autonomous Engineering Org      | 🔜     |

---

## Progress Overview

```
v0.1 Foundation ████████████████████ 100%
v0.2 Kernel Platform ████████████████████ 100%
v0.3 Runtime & Safety ████████████████████ 100%
v0.4 Repository Platform ████████████████████ 100%
v0.5 Source Intelligence ████████████████████ 100%
v0.6 Engineering Platform ████████████████████ 100%
v0.7 Planning Intelligence ████████████████████ 100%
v0.8 Semantic Transformations ████████████████████ 100%
v0.9 Chief Engineer ████████████████████ 100%
v0.91 Benchmark Platform ████████████████████ 100%
v1.0 Workers ░░░░░░░░░░░░░░░░░░░░ 0%
v1.1 Autonomous Org ░░░░░░░░░░░░░░░░░░░░ 0%
```


---

## Post‑1.0 Vision

After v1.0, EAG will evolve toward:

- **Multi‑repository coordination** — Understand and reason across multiple repositories
- **Cloud execution** — Run workers and the Chief Engineer in cloud environments
- **Persistent Knowledge Graph** — Store engineering knowledge for long‑term, cross‑session memory
- **Plugin Marketplace** — A first‑class ecosystem for reusable transformations and tools
- **Continuous Engineering** — Always‑on monitoring and autonomous improvement
- **Self‑improvement** — EAG learns from its own execution history
- **Human collaboration** — Seamless handoff between autonomous agents and human engineers
- **Team orchestration** — Multiple EAG instances cooperating on large‑scale engineering tasks

---

## Guiding Principles for Roadmap Planning

1. **Architecture before implementation** — Every sprint begins with a design document.
2. **Knowledge before action** — EAG must understand before it acts.
3. **Safety scales with capability** — Every new capability must pass through the Safety Runtime.
4. **Documentation evolves with implementation** — Each sprint updates all relevant docs.
5. **Always leave the project better than it was found** — Each sprint improves architecture, tests, and documentation.
