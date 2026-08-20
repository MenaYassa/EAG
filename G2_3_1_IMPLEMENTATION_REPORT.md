# EAG G2.3.1 — Governed Mutation Foundation Implementation Report

**Date:** 20 August 2026
**Baseline:** `v2.2.0-g2.2` at `c7e361be7fef3a51871291b1cf94b4cdb05ec186`
**Scope:** Deterministic mutation foundation only. No LLM, Chief, Coordinator, Planner, gateway, workspace-runtime, capability-runtime, Git, shell, network, or provider integration was added.

> **Result:** G2.3.1 establishes a deterministic `ChangeProposal → Mutation Policy → Mutation Authorization → Governed Workspace Mutation → MutationReceipt` boundary for exactly two operations: safe file creation and safe full-file modification. Every proposal is treated as untrusted input.

## 1. Delivered Contracts

| Contract | Delivered behavior |
|---|---|
| `ChangeProposal` | Immutable, non-executable untrusted proposal with run/decision IDs, target, operation, content fingerprint, precondition, reason, provenance, risk, metadata, expected postcondition, state fingerprints, and deterministic digest. |
| Mutation policy | Fail-closed validation of relative paths, root confinement, traversal, symlink parent/target, sensitivity, proposed-content secrets, sizes, operation semantics, target type, create-existing rejection, modify-missing rejection, and stale fingerprints. |
| Authorization | Immutable authorization bound to exact proposal digest, operation, path, workspace fingerprint, repository snapshot fingerprint, and policy version; one-time consumed state is required before write. |
| Mutation mechanics | A local, atomic temporary-file replacement strategy writes exactly one authorized UTF-8 text target. Parent directories are never implicitly created. |
| Preconditions | Modify requires exact current content fingerprint; create requires absence. State is revalidated immediately before authorization consumption and write. |
| Verification | Requires expected target existence and proposal-content fingerprint after write. A failed postcondition conditionally compensates only while the target remains exactly at this mutation’s observed post-state. |
| `MutationReceipt` | Immutable and content-free terminal audit record with IDs, path/operation, pre/post fingerprints, byte counts, authorization state, policy version, result, sanitized failure, verification, and rollback status. |
| Events | Shared-event-bus lifecycle events: proposed, authorized, started, rejected, completed, and failed; no raw proposed content, provider output, prompt, secrets, or absolute host paths. |

## 2. Explicit Safety Boundary

The first slice allows only `create_file` and `modify_file` on a single safe UTF-8 file. It rejects absolute paths, `..`, path escape, missing parents, symlink parents/targets, non-regular/binary/non-UTF-8 targets, sensitive files, sensitive proposed content, oversized targets/content, stale preconditions, unsupported operations, existing create targets, missing modify targets, and mismatched or reused authorization.

No generic patch engine was introduced. No operation deletes, renames, moves, copies, creates directories, changes permissions, invokes shell commands, performs Git actions, uses the network, accesses credentials, or grants an LLM filesystem authority. The existing `WorkspaceRuntime`, `CapabilityRuntime`, Chief, Coordinator, Scheduler, LLM gateway, repository intelligence, EBS-014, and provider configuration remain unchanged.

## 3. Deterministic EBS-015 Contract

A tiny isolated `tests/fixtures/ebs_015_governed_patch/` fixture and `tests/test_ebs_015_governed_patch_synthesis.py` establish a non-live EBS-015 contract. It proves a bounded fixture proposal traverses policy, authorization, atomic mutation, receipt, and deterministic verification without a provider, shell, Git, or network.

This is **not** a live LLM mutation benchmark and must not be reported as one.

## 4. Test Coverage

The new deterministic suite covers valid creation/modification, traversal/absolute-path rejection, symlink parent and target rejection, sensitive path/content rejection, unsupported operation, oversized content, stale precondition, create-existing rejection, authorization mismatch/reuse, postcondition compensation, write-failure receipt, receipt redaction, event ordering, unchanged non-target workspace content, repeated deterministic behavior, and explicit no-shell/Git/network execution.

| Validation | Result |
|---|---|
| G2.3.1 mutation + deterministic EBS-015 tests | **24 passed** |
| G2.3.1 + G2.2 context/gateway targeted group | **64 passed, 1 skipped** |
| Dedicated autonomous suite | **3 passed** |
| Normal EBS suite | **7 passed, 2 skipped**; credentialed EBS-013/EBS-014 remain opt-in skips |
| Full pytest suite | **3481 passed, 3 skipped** |
| Ruff on G2.3.1 touched files | **PASS** |
| MyPy on `src/eag/mutation` | **PASS** — 7 source files |
| `git diff --check` | **PASS** |

## 5. Explicit Non-Execution Record

```text
LLM_MUTATION_ENABLED=NO
EBS_014_RERUN=NO
EBS_015_LIVE=NO
CAPABILITY_RUNTIME_INTEGRATION=NO
CHIEF_COORDINATOR_INTEGRATION=NO
SHELL_INVOCATIONS_BY_MUTATION_RUNTIME=0
GIT_MUTATIONS_BY_MUTATION_RUNTIME=0
NETWORK_INVOCATIONS_BY_MUTATION_RUNTIME=0
```

## 6. Files Added

| Area | Files |
|---|---|
| Mutation domain | `src/eag/mutation/__init__.py`, `models.py`, `errors.py`, `policy.py`, `authorization.py`, `events.py`, `runtime.py` |
| Safety/contract tests | `tests/test_governed_mutation.py` |
| Deterministic benchmark contract | `tests/test_ebs_015_governed_patch_synthesis.py`, `tests/fixtures/ebs_015_governed_patch/article.py` |
| Report | `G2_3_1_IMPLEMENTATION_REPORT.md` |

## 7. Required Status

```text
G2.3.1_IMPLEMENTATION=COMPLETE
CHANGE_PROPOSAL=PASS
MUTATION_POLICY=PASS
AUTHORIZATION_BOUNDARY=PASS
WORKSPACE_SAFETY=PASS
MUTATION_RECEIPT=PASS
TESTS=24 passed
FULL_SUITE=3481 passed, 3 skipped
RUFF=PASS
MYPY=PASS

LLM_MUTATION_ENABLED=NO
EBS_014_RERUN=NO
EBS_015_LIVE=NO

COMMIT=NOT_PERFORMED
PUSH=NOT_PERFORMED
TAG=NOT_CREATED
```
