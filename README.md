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

**Version:** 0.5 — Engineering Graph Platform
| Milestone | Status |
| --- | --- |
| Sprint 0 — Foundation | ✅ Complete |
| Sprint 1 — Kernel & Plugin Platform | ✅ Complete |
| Sprint 2 — Execution Platform | ✅ Complete |
| Sprint 3 — Safety & Engineering Runtime | ✅ Complete |
| Sprint 4 — Engineering Knowledge Platform | ✅ Complete |
| Sprint 5 — Planner Engine | 🔜 Next |

### Implemented Capabilities

*   **Kernel** — Central coordinator managing lifecycle, dependency injection, and runtime context
    
*   **Event Bus** — Internal pub/sub system coordinating all runtime services
    
*   **Execution Runtime** — Session management, changesets, and task execution
    
*   **Safety Runtime** — Destructive-action detection, human approval gates, guardrails
    
*   **Repository Runtime** — Repository scanning, profiling, framework detection
    
*   **Source Runtime** — Symbol analysis, import tracking, call graph extraction
    
*   **Engineering Index** — Semantic index of all discovered symbols, files, and relationships
    
*   **Engineering Graph** — Directed graph of engineering relationships with impact analysis, explainability, and pathfinding
    

### Upcoming

*   **Planner Engine** — Goal decomposition, planning models, execution plans, validation, approval, and dry run
    
*   **Chief Engineer** — Model routing, tool selection, multi-model coordination
    
*   **Workers** — Parallel execution, collaboration, and multi-agent task completion
    

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

*   **Planner Engine** — Goal decomposition, planning models, dry-run, and validation
    
*   **Chief Engineer** — Model-agnostic routing, tool selection, and coordination
    
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

EAG is under active development. The platform has completed four sprints  
and is preparing for Sprint 5 — the Planner Engine, which will add goal  
decomposition, planning models, execution plans, validation, approval  
flows, and dry-run capabilities.
For the complete development plan, see [ROADMAP.md](docs/ROADMAP.md).