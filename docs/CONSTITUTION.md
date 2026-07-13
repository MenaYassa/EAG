# EAG Constitution

* * *

## Mission

Build an open software engineering operating system that coordinates  
intelligent workers to solve engineering problems safely, transparently,  
and sustainably.

* * *

## Immutable Principles

1.  **Model agnostic.** EAG must never depend on a single AI model,  
    provider, or vendor. Any model that can follow instructions can be used.
    
2.  **Plugin first.** Every capability beyond the core is a plugin. The  
    platform is extended, not modified.
    
3.  **Knowledge is permanent.** Once engineering knowledge is discovered —  
    a symbol, a relationship, an impact — it is never lost. Knowledge is  
    persisted, not recomputed.
    
4.  **Reason before execution.** No change is applied without reasoning  
    about its impact. EAG must understand what will change and why before  
    it acts.
    
5.  **Human approval for destructive actions.** Any operation that deletes,  
    overwrites, or irreversibly modifies state requires explicit human  
    approval. No exceptions.
    
6.  **Every action must be explainable.** Every operation — from graph  
    construction to code execution — must produce a human-readable  
    explanation of what it did and why.
    
7.  **Core never depends on plugins.** The plugin boundary is  
    one-directional. Plugins depend on the core; the core never depends on  
    plugins. Removing a plugin must never break EAG.
    
8.  **Architecture before implementation.** Every feature begins with a  
    design. Implementation follows architecture, not the other way around.
    
9.  **Documentation evolves with implementation.** Documentation is not  
    an afterthought. It is part of the definition of done for every feature.
    
10.  **Always leave the project better than it was found.** Every change —  
     every PR, every commit — must improve the project in some way beyond  
     its immediate purpose.
     
11.  **Engineering knowledge is deterministic.** The same repository, scanned  
     and indexed, must always produce the same engineering knowledge. There  
     is no randomness or ambiguity in facts.
     
12.  **AI consumes engineering knowledge but never replaces it.** AI models  
     assist in understanding and acting, but engineering knowledge is the  
     source of truth — not the model's interpretation of it.
     
13.  **Separate facts, reasoning, and execution.** Facts (what the repository  
     is) are immutable. Reasoning (what should change) is transient and  
     auditable. Execution (how to change) is controlled and gated. These  
     three layers never blur.
     
14.  **Runtime orchestrates. Algorithms reason. Builders construct.** Each  
     component has a single role. Runtimes coordinate lifecycle and events.  
     Algorithms analyze, score, and explain. Builders construct objects.  
     No component takes on a role that belongs to another.
     

* * *

## Engineering Ethics

EAG always favors:

*   **Maintainability** — Code must be understandable and changeable by any  
    engineer, including future AI agents.
    
*   **Readability** — Clarity over cleverness. If a comment is needed to  
    explain _what_ the code does, the code is wrong. If a comment explains  
    _why_, the comment is needed.
    
*   **Testability** — Every component must be testable in isolation. If it  
    isn't, the design is wrong.
    
*   **Security** — Safety gates are never bypassed. Human approval for  
    destructive actions is always required.
    
*   **Simplicity over cleverness** — The simplest correct solution is always  
    preferred. Cleverness is a liability.
    

* * *

## Separation of Concerns

| Layer | Role | Examples |
| --- | --- | --- |
| Facts | What the repository is | RepositoryProfile, SourceAnalysis, EngineeringIndex, EngineeringGraph |
| Reasoning | What should change | Planner, ImpactAnalysis, Explainability, Pathfinding |
| Execution | How to change | ExecutionRuntime, Changesets, SafetyGates |

Facts are immutable and persistent. Reasoning is transient and auditable.  
Execution is controlled and gated. These three layers must remain  
independent at all times.

* * *

## Amendment

This Constitution may not be amended, superseded, or suspended. New  
principles may be added but existing principles may never be removed or  
weakened. This is the social contract of EAG.

* * *

## Acknowledgement

Contributors to EAG implicitly accept this Constitution. All code review,  
architecture decisions, and project direction must preserve these  
principles without exception.