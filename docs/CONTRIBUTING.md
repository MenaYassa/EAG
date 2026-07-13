# Contributing to EAG

Thank you for your interest in contributing to EAG. This document  
describes how to contribute effectively to the project.

* * *

## Development Philosophy

EAG is built with a specific set of engineering principles. Every  
contributor is expected to understand and follow them.

### Core Principles

*   **Architecture first** — Before writing code, ensure the architecture  
    supports the change. If it doesn't, propose an architectural change first.
    
*   **Small focused pull requests** — One PR should address one concern.  
    Large PRs that mix concerns will be rejected.
    
*   **Tests required** — Every feature and bug fix must include tests. EAG  
    is developed test-first for nearly every subsystem.
    
*   **Documentation updated with every feature** — If you add or change a  
    feature, update the relevant documentation in the same PR.
    
*   **All changes must preserve the Constitution** — See  
    [CONSTITUTION.md](CONSTITUTION.md) for the immutable principles.
    

### Engineering Principles

| Principle | Meaning |
| --- | --- |
| Runtime owns lifecycle | Each runtime controls its own startup, shutdown, and state management |
| Models are immutable | Data structures are never mutated in place. Return new instances. |
| Builders build | Builders construct objects. They do not reason or make decisions. |
| Algorithms reason | Algorithms analyze, score, and explain. They do not execute changes. |
| Services support | Services provide infrastructure: I/O, persistence, coordination. |
| Events coordinate | Runtimes communicate through EventBus, never through direct calls. |

* * *

## Definition of Done

A feature is considered complete only when **all** of the following are true:
| Criterion | Tool / Standard |
| --- | --- |
| Linting passes | `ruff check .` — zero errors |
| Type checking passes | `mypy .` — zero errors |
| Tests pass | `pytest` — 100% pass rate, no skipped tests without justification |
| Documentation updated | All relevant docs reflect the new feature |
| CLI updated (if applicable) | New commands or flags are wired and documented |
| Architecture review | The change is reviewed for architectural consistency |
| Constitution preserved | No immutable principle is violated |

* * *

## Testing Philosophy

EAG is developed test-first. Nearly every subsystem is built by writing  
tests before implementation. This is not a suggestion — it is how the  
project maintains its quality and architectural integrity.

### Why Test-First?

1.  **Tests are the first client** — Writing tests first forces you to think  
    about the interface, not the implementation.
    
2.  **Immutable models are easy to test** — Since models never mutate, tests  
    are deterministic and repeatable.
    
3.  **Runtimes are isolated** — Each runtime communicates through EventBus,  
    making them easy to test in isolation with mock events.
    
4.  **Algorithms are pure** — Graph algorithms take inputs and return outputs  
    with no side effects, making them trivial to test.
    

### Test Structure

```
tests/
├── unit/
│   ├── test_kernel.py
│   ├── test_event_bus.py
│   ├── test_safety_runtime.py
│   ├── test_repository_runtime.py
│   ├── test_source_runtime.py
│   ├── test_index_runtime.py
│   ├── test_graph_runtime.py
│   └── test_execution_runtime.py
├── integration/
│   ├── test_knowledge_flow.py
│   ├── test_execution_flow.py
│   └── test_safety_gates.py
├── algorithms/
│   ├── test_impact_analysis.py
│   ├── test_explainability.py
│   ├── test_pathfinding.py
│   ├── test_centrality.py
│   └── test_cycle_detection.py
└── fixtures/
    ├── sample_repo/
    └── sample_graphs/
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=eag --cov-report=term-missing

# Specific module
pytest tests/unit/test_graph_runtime.py

# Algorithms only
pytest tests/algorithms/
```

* * *

## Pull Request Checklist

Before submitting a PR, verify:

### Architecture

- [ ] [ ] 

Change follows the layered architecture

- [ ] [ ] 

No runtime calls another runtime directly (use EventBus)

- [ ] [ ] 

Models are immutable

- [ ] [ ] 

Core does not depend on plugins

- [ ] [ ] 

No immutable principle is violated

### Tests

- [ ] [ ] 

Tests written and passing

- [ ] [ ] 

Edge cases covered

- [ ] [ ] 

No skipped tests without justification

- [ ] [ ] 

Coverage maintained or improved

### Documentation

- [ ] [ ] 

Relevant docs updated (ARCHITECTURE.md, README.md, CHANGELOG.md)

- [ ] [ ] 

CLI help text updated (if applicable)

- [ ] [ ] 

Docstrings added for new public APIs

### Performance

- [ ] [ ] 

No unnecessary re-computation

- [ ] [ ] 

Graph algorithms have expected complexity

- [ ] [ ] 

No blocking calls in event handlers

### Backward Compatibility

- [ ] [ ] 

Existing CLI commands still work

- [ ] [ ] 

Existing models still parse correctly

- [ ] [ ] 

Existing plugins still load

* * *

## Contribution Workflow

1.  **Fork** the repository
    
2.  **Branch** from `main` — use a descriptive branch name:
    *   `feature/planner-engine`
        
    *   `bugfix/graph-cycle-detection`
        
    *   `docs/architecture-update`
        
3.  **Implement** following the engineering principles
    
4.  **Test** — write tests first, then implement until tests pass
    
5.  **Update documentation** — update all relevant docs in the same PR
    
6.  **Submit PR** — include a description of what changed and why
    

* * *

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add impact analysis algorithm to GraphRuntime
fix: resolve edge case in cycle detection for self-referencing imports
docs: rewrite README for Engineering Platform v0.5
refactor: extract symbol resolution into IndexRuntime
test: add integration tests for knowledge flow pipeline
chore: update ruff configuration
```

* * *

## Code Review

All changes should preserve the Constitution.
Reviewers will check:

*   **Architectural consistency** — Does the change fit the layered architecture?
    
*   **Immutability** — Are models treated as immutable?
    
*   **Event-driven communication** — Do runtimes communicate through EventBus?
    
*   **Safety** — Does the change respect safety gates?
    
*   **Explainability** — Are all new operations explainable?
    
*   **Test coverage** — Are tests meaningful, not just present?
    
*   **Documentation** — Is documentation updated and accurate?
    
*   **Backward compatibility** — Does the change break existing functionality?
    

* * *

## Development Environment

### Prerequisites

*   Python 3.11+
    
*   pip or uv
    

### Setup

```bash
# Clone
git clone https://github.com/your-org/eag.git
cd eag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run linting
ruff check .
mypy .

# Run tests
pytest
```

### Useful Commands

```bash
# Scan a test repository
eag scan --path tests/fixtures/sample_repo

# Index it
eag index

# Build the graph
eag graph

# Query impact
eag impact sample_function

# Explain a symbol
eag why SampleClass
```

* * *

## Questions?

*   Read the [Constitution](CONSTITUTION.md) for project principles
    
*   Read the [Architecture](ARCHITECTURE.md) for technical details
    
*   Read the [Engineering Platform Guide](ENGINEERING_PLATFORM.md) for a subsystem walkthrough
    
*   Read the [Roadmap](ROADMAP.md) for future plans
    
*   Open an issue for specific questions