# EAG — Engineering Operating System

> An open, model-agnostic engineering operating system that coordinates  
> intelligent workers to understand repositories, plan changes, and  
> execute engineering tasks safely, transparently, and sustainably.

* * *

## What EAG Is

EAG is not a coding assistant. It is a **platform** — an operating system  
for engineering work. It understands repositories the way an engineer  
does: by scanning source files, building semantic indexes, constructing  
engineering graphs, and reasoning about relationships, dependencies, and  
impact before any change is made.
EAG is built around a kernel-and-runtime architecture. Each capability —  
repository scanning, source analysis, index building, graph construction,  
safety checks, execution — is a runtime service that coordinates through an  
internal event bus. The core never depends on plugins, and every action is  
explainable.

* * *

## Current Status

**Version:** 1.0 — Autonomous Multi-Agent Workers
| Milestone | Status |
| --- | --- |
| Sprint 0 — Foundation | ✅ Complete |
| Sprint 1 — Kernel Platform | ✅ Complete |
| Sprint 2 — Runtime Platform | ✅ Complete |
| Sprint 3 — Safety & Repository Platform | ✅ Complete |
| Sprint 4 — Source Intelligence Platform | ✅ Complete |
| Sprint 5 — Planner Platform | ✅ Complete |
| Sprint 6 — Engineering Platform | ✅ Complete |
| Sprint 7 — Chief Engineer | ✅ Complete |
| EBS-0 Benchmark Platform | ✅ Complete |
| Sprint 8 — Workers | ✅ Complete |
| Sprint 9 — Autonomous Engineering | ⏳ In Progress |
| Sprint 10 — Autonomous Software Engineering | 🔜 Next |

### Published Gen2 Governed Boundary Status

The following published Gen2 chain separates immutable evidence, durable transition control, and one narrowly bounded local construction authority from the legacy autonomous and generic execution paths. It does **not** introduce an external transition executor.

| Milestone | Published tag | Current status | Boundary contribution |
| --- | --- | --- | --- |
| G2.4.14 — Artifact Readiness | `v2.4.14-g2.4.14` | Complete / published | Immutable artifact readiness evidence. |
| G2.4.15 — Promotion Eligibility | `v2.4.15-g2.4.15` | Complete / published | Governed logical-destination promotion eligibility evidence. |
| G2.4.16 — External Transition Authorization | `v2.4.16-g2.4.16` | Complete / published | Immutable human external-transition authorization evidence. |
| G2.4.17 — Transition Control Ledger | `v2.4.17-g2.4.17` | Complete / published | Sole durable, fail-closed pre-execution transition-control ledger. |
| G2.4.18 — Destination Contract Evidence | `v2.4.18-g2.4.18` | Complete / published | Immutable, deterministic destination-contract evidence with typed exact request/assessment provenance. |
| G2.4.19 — Outcome-Semantics Policy Evidence | `v2.4.19-g2.4.19` | Complete / published | Immutable, deterministic outcome-semantics policy evidence with typed exact request/assessment provenance and outcome-unknown safety. |
| G2.4.20 — Attestation-Policy Evidence | `v2.4.20-g2.4.20` | Complete / published | Declared destination-contract attestation-policy evidence only; it does not establish trust, issuer authentication, signature verification, destination truth, or execution readiness. |
| G2.4.21 — Construction Work-Order Evidence | `v2.4.21-g2.4.21` (original) and `v2.4.21-provenance.1` (remediation) | Complete / published | Immutable local construction work-order evidence binding exact upstream evidence, custody/composition declarations, intent digests, capabilities, limits, identity, and expiry; its follow-up remediation adds typed exact request/assessment provenance. |
| G2.4.22 — Bounded Workspace File Construction | `v2.4.22-g2.4.22` | Complete / published | Bounded create-only descriptor-relative text-file construction, consuming one published G2.4.10 live custody handoff and exact G2.4.21 typed work-order provenance. |

The current governed progression is:

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
Bounded Workspace File Construction
```

G2.4.17 remains the sole durable pre-execution transition-control ledger for its existing external-artifact-transition profile. G2.4.18 remains destination-contract evidence only, G2.4.19 remains outcome-semantics policy evidence only, and G2.4.20 remains declared attestation-policy evidence only; none establishes trust, issuer authentication, signature verification, destination truth, or execution readiness. The typed provenance remediation across G2.4.18–G2.4.21 closes request/assessment substitution gaps without inferring provenance from generic evidence references. The original G2.4.21 milestone remains `v2.4.21-g2.4.21` at `e8931c5dc196d25a4741447d5b4580a7f84ead4d`; the accepted G2.4.21 remediation was published at `55c9d02e698558bbf7f68773207c3c80b9995b3d` under immutable tag `v2.4.21-provenance.1`, with the original tag unchanged. G2.4.22 was published at `14f42717be5e819f41ee0369e93417303b5753b3` under immutable tag `v2.4.22-g2.4.22`.

G2.4.10 remains the sole owner of custody acquisition, live descriptor continuity, issued-handle provenance, and handle lifecycle. G2.4.21 remains the sole owner of typed construction-work-order request/assessment provenance. G2.4.22 neither reopens a workspace pathname nor reconstructs a descriptor or handle provenance; after immutable authorization and capability checks, it consumes the one matching G2.4.10 handoff and performs only declared descriptor-relative, `O_NOFOLLOW` and `O_EXCL` create-only file effects. It creates no workspace root and has no overwrite, delete, move, copy, permission-change, command, build, dependency, browser, network, credential, session, permit, ledger, release, or deployment authority.

G2.4.22 issues immutable receipts only for the successfully completed ordered action prefix. A definitive pre-create failure is a `CONSTRUCTION_REFUSED` result with no action receipt; an effect-started or uncertain post-create failure is `PARTIAL_CONSTRUCTION_STOPPED` with no receipt for the unsuccessful action. The first failure is terminal: there is no retry, rollback, cleanup, recovery, or reconciliation. EBS-037 final acceptance directly proves descriptor continuity after pathname replacement, pre-create refusal, effect-started failure, truthful receipts, capability refusal, and forged/closed/consumed handle refusal. The evidence classifications remain truthful: `OBSERVED_ZERO_EFFECT_CATEGORIES=NONE`; unavailable operational categories are `CAPABILITY_ABSENT`; and immutable evidence, receipts, and test-owned filesystem state are `DIRECT_STATE_PROOF`. `G2.4.23=NOT_STARTED`.

### Implemented Capabilities

*   **Kernel** — Central coordinator managing lifecycle, dependency injection, and runtime context
    
*   **Event Bus** — Internal pub/sub system coordinating all runtime services
    
*   **Execution Runtime** — Session management, changesets, and task execution
    
*   **Safety Runtime** — Destructive-action detection, human approval gates, guardrails
    
*   **Repository Runtime** — Repository scanning, profiling, framework detection
    
*   **Source Runtime** — Symbol analysis, import tracking, call graph extraction
    
*   **Engineering Index** — Semantic index of all discovered symbols, files, and relationships
    
*   **Engineering Graph** — Directed graph of engineering relationships with impact analysis, explainability, and pathfinding
    
*   **Planner Engine** — Goal decomposition, planning models, execution plans, validation, approval, and dry run

*   **Chief Engineer** — Model routing, tool selection, multi-model coordination

*   **Benchmark Platform** — EBS-0 suite with 5 benchmarks

*   **Workers** — Parallel execution, collaboration, and multi-agent task completion (Worker Runtime, Registry, Scheduler)
*   **Engineering Memory** — Reflection engine and persistent lessons learned

### Upcoming
    
*   **Autonomous Engineering** — Evolving from an autonomous engineer to an autonomous engineering organization


* * *

## Quick Start

### Installation

```bash
pip install eag
```

### Initialize EAG in a Repository

```bash
cd your-repository
eag init
```

### Scan and Index a Repository

```bash
eag scan              # Scan repository structure and detect frameworks
eag symbols <file>    # Extract symbols from a specific file
eag index             # Build the engineering index
eag graph             # Construct the engineering graph
```

### Query Engineering Knowledge

```bash
eag impact <symbol>   # Analyze the impact of changing a symbol
eag why <symbol>      # Explain why a symbol exists and what depends on it
eag path <a> <b>      # Find the dependency path between two symbols
```

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Presentation Layer                 │
│          CLI · API · Open WebUI                 │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                   EAG Kernel                    │
│  ┌──────────────────────────────────────────┐   │
│  │           Runtime Context                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Safety  │ │Repository│ │  Source  │  │   │
│  │  │ Runtime  │ │ Runtime  │ │ Runtime  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Index   │ │  Graph   │ │Execution │  │   │
│  │  │ Runtime  │ │ Runtime  │ │ Runtime  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘  │   │
│  └──────────────────────────────────────────┘   │
│              Tool Registry                      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Plugins / Providers                │
└─────────────────────────────────────────────────┘
```

Each runtime service coordinates through the EventBus. The Kernel manages  
lifecycle and dependency injection. No runtime depends on plugins; plugins  
extend the platform through the Tool Registry.
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architectural specification  
and [ENGINEERING_PLATFORM.md](docs/ENGINEERING_PLATFORM.md) for the platform guide.

* * *

## Why EAG Exists

Modern coding agents are powerful, but they are tightly coupled to specific  
models and workflows. EAG aims to become a model-agnostic engineering  
operating system capable of understanding repositories, planning changes,  
coordinating specialized workers, and executing tasks safely.
EAG separates facts (what the repository is), reasoning (what should  
change and why), and execution (how to change it safely). This separation  
is what makes EAG safe, explainable, and sustainable.

* * *

## Planned Features

*   **Worker Coordination** — Parallel execution and multi-agent collaboration
    
*   **Multi-model Routing** — Route tasks to the best available model
    
*   **Plugin SDK** — First-class plugin development toolkit
    
*   **Infrastructure Management** — Manage deployment targets and environments
    
*   **Documentation Automation** — Generate and maintain documentation from code
    

* * *

## Documentation

| Document | Purpose |
| --- | --- |
| [CONSTITUTION.md](docs/CONSTITUTION.md) | Mission, immutable principles, ethics |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full architectural specification |
| [ENGINEERING_PLATFORM.md](docs/ENGINEERING_PLATFORM.md) | Platform guide — every subsystem explained |
| [ROADMAP.md](docs/ROADMAP.md) | Sprint plan and version goals |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development philosophy and contribution workflow |
| [CHANGELOG.md](docs/CHANGELOG.md) | Release history |

* * *

## Engineering Principles

EAG is governed by a [CONSTITUTION.md](docs/CONSTITUTION.md) with ten immutable  
principles:

1.  Model agnostic
    
2.  Plugin first
    
3.  Knowledge is permanent
    
4.  Reason before execution
    
5.  Human approval for destructive actions
    
6.  Every action must be explainable
    
7.  Core never depends on plugins
    
8.  Architecture before implementation
    
9.  Documentation evolves with implementation
    
10.  Always leave the project better than it was found
     

* * *

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for the full guide. In short:

*   Architecture first
    
*   Small focused pull requests
    
*   Tests required
    
*   Documentation updated with every feature
    
*   All changes must preserve the Constitution
    

**Workflow:** Fork → Branch → Implement → Test → Update docs → Submit PR

* * *

## License

MIT

* * *

## Project Status

EAG is under active development. The platform has completed up to Sprint 8 (Workers) and Sprint 9.2 (Engineering Memory), evolving EAG into an autonomous engineering organization with reflection capabilities.
We are now preparing for Sprint 9.3 (Adaptive Planning) and Sprint 10 (Autonomous Software Engineering).
For the complete development plan, see [ROADMAP.md](docs/ROADMAP.md).