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

## Published Gen2 Governed Boundary Progression

The following milestones are published, evidence-oriented Gen2 boundaries. They preserve the existing autonomous and generic execution paths and do not form an external transition executor.

| Milestone | Status | Published tag | Boundary |
| --- | --- | --- | --- |
| G2.4.14 — Artifact Readiness | Complete / published | `v2.4.14-g2.4.14` | Proves immutable artifact readiness evidence. |
| G2.4.15 — Promotion Eligibility | Complete / published | `v2.4.15-g2.4.15` | Proves promotion eligibility for a logical destination. |
| G2.4.16 — External Transition Authorization | Complete / published | `v2.4.16-g2.4.16` | Proves immutable external-transition authorization evidence. |
| G2.4.17 — External Transition Control Ledger | Complete / published | `v2.4.17-g2.4.17` | Sole durable, fail-closed pre-execution transition-control ledger. |
| G2.4.18 — External Destination Contract Evidence | Complete / published | `v2.4.18-g2.4.18` | Immutable destination-contract evidence with typed exact request/assessment provenance. |
| G2.4.19 — Outcome-Semantics Policy Evidence | Complete / published | `v2.4.19-g2.4.19` | Immutable policy evidence defining safe future outcome semantics, typed exact provenance, and outcome-unknown safety. |
| G2.4.20 — Attestation-Policy Evidence | Complete / published | `v2.4.20-g2.4.20` | Declared destination-contract attestation-policy evidence only; no trust, issuer authentication, signature verification, destination truth, or execution readiness. |
| G2.4.21 — Construction Work-Order Evidence | Complete / published | `v2.4.21-g2.4.21` | Immutable local construction work-order evidence binding exact upstream evidence, custody/composition declarations, intent digests, capabilities, limits, identity, and expiry. |
| G2.4.22 | Not started | — | No reconnaissance, design, implementation, or testing is underway. |

```text
Artifact Readiness
        ↓
Promotion Eligibility
        ↓
External Transition Authorization
        ↓
External Transition Control Ledger
        ↓
External Destination Contract Evidence
        ↓
External Outcome-Semantics Policy Evidence
        ↓
Declared Attestation-Policy Evidence
        ↓
Construction Work-Order Evidence
        ↓
[G2.4.22 — not started]
```

G2.4.17 remains the sole durable pre-execution transition-control ledger for its existing external-artifact-transition profile. G2.4.18 and G2.4.19 carry typed exact request/assessment provenance; G2.4.20 is declared attestation-policy evidence only; and G2.4.21 is local construction work-order evidence only. The typed provenance remediation through G2.4.21 closed request/assessment substitution gaps without generic evidence-reference inference.

G2.4.21 does not execute construction: it creates or leases no workspace, writes no file, runs no command, installs no dependency, invokes no runtime, accesses no credential/network, builds/tests no application, and performs no correction, retry, rollback, recovery, reconciliation, publication, release, or deployment. The B5/B6 evidence classification remains truthful: `OBSERVED_ZERO_EFFECT_CATEGORIES=NONE`; operational categories are `CAPABILITY_ABSENT`; and immutable evidence, policy, request, result, and test-owned state are established through `DIRECT_STATE_PROOF`. `G2.4.22=NOT_STARTED`.

## Upcoming Sprints

### Sprint 8 — Workers ✅

Workers become a full‑fledged distributed execution system.

- **8.1** Worker Runtime
- **8.2** Worker Registry
- **8.3** Worker Collaboration
- **8.4** Scheduler
- **8.5** Parallel Execution
- **8.6** Multi-worker Platform

**Target Version:** v1.0

---

### Sprint 9 — Autonomous Engineering ⏳

Evolving from an autonomous engineer to an autonomous engineering organization.

- **9.1** Reflection Engine ✅
- **9.2** Engineering Memory ✅
- **9.3** Adaptive Planning 🔜
- **9.4** Autonomous Engineering Loop 🔜

**Target Version:** v1.1

---

### Sprint 10 — Autonomous Software Engineering 🔜

Let EAG engineer real software autonomously.

- End-to-end repository creation and lifecycle management
- High-level multi-repository reasoning
- Real-world autonomous execution

**Target Version:** v2.0

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
| v1.0    | Autonomous Multi‑Agent Workers  | ✅     |
| v1.1    | Autonomous Engineering Org      | ⏳     |
| v2.0    | Autonomous Software Engineering | 🔜     |

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
v1.0 Workers ████████████████████ 100%
v1.1 Autonomous Org ██████████░░░░░░░░░░ 50%
v2.0 Auto Software ░░░░░░░░░░░░░░░░░░░░ 0%
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
