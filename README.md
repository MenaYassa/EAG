# EAG --- Engineering Agent

> **The Operating System for AI Engineers**

## Vision

EAG (Engineering Agent, codename **Eager for Knowledge**) is an open,
modular software engineering platform designed to coordinate AI workers
rather than simply generate code.

Unlike traditional coding assistants, EAG separates **Knowledge**,
**Reasoning**, and **Execution** into independent cores, allowing the
platform to evolve independently of any AI model.

## Why EAG Exists

Modern coding agents are powerful, but they are tightly coupled to
specific models and workflows. EAG aims to become a model-agnostic
engineering operating system capable of understanding repositories,
planning changes, coordinating specialized workers, and executing tasks
safely.

## Core Principles

-   Knowledge over memory
-   Reason before execution
-   Humans remain in control
-   Model agnostic
-   Plugin-first architecture
-   Explainable decisions
-   Safety by default

## High-Level Architecture

``` text
User
 │
 ▼
Open WebUI / CLI / API
 │
 ▼
EAG Core
 ├── Knowledge Core
 ├── Reasoning Core
 └── Execution Core
 │
 ▼
Tool Registry
 │
 ├── Git
 ├── Docker
 ├── Filesystem
 ├── Database
 ├── Browser
 └── ...
```

## Planned Features

-   Repository Intelligence
-   Knowledge Graph
-   Engineering Planner
-   Multi-model routing
-   Plugin SDK
-   Multi-agent execution
-   Infrastructure management
-   Documentation automation

## Project Status

Current milestone: **Sprint 0 -- Foundation**

The first implementation focuses on the platform foundation before
advanced engineering capabilities.

## Documentation

-   CONSTITUTION.md
-   ARCHITECTURE.md
-   ROADMAP.md
-   CONTRIBUTING.md
-   CHANGELOG.md

## License

To be decided (MIT vs Apache-2.0).
