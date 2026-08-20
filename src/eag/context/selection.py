"""Deterministic, bounded repository-context selection without model or capability execution."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from eag.context.fingerprint import context_fingerprint
from eag.context.models import (
    ContextBudget,
    ContextProvenanceRecord,
    ContextTruncationReport,
    DependencyReference,
    FileReference,
    RepositoryContextSnapshot,
    SelectedRepositoryContext,
    SourceArtifactRecord,
    SourceExcerpt,
    SymbolReference,
)
from eag.context.sensitivity import ContextSecurityPolicy
from eag.source.models import Dependency, Symbol


@dataclass(frozen=True, slots=True)
class _Candidate:
    score: int
    reason: str


class ContextSelector:
    """Projects factual repository evidence using a stable goal-aware ranking policy."""

    def select(
        self,
        *,
        goal: str,
        snapshot: RepositoryContextSnapshot,
        budget: ContextBudget,
        security_policy: ContextSecurityPolicy,
    ) -> SelectedRepositoryContext:
        if not goal.strip():
            raise ValueError("goal cannot be empty")
        goal_lower = goal.lower()
        tokens = _goal_tokens(goal_lower)
        artifacts = {artifact.repository_path: artifact for artifact in snapshot.source_artifacts}
        file_candidates = self._file_candidates(goal_lower, tokens, artifacts)
        symbol_candidates = self._symbol_candidates(goal_lower, tokens, snapshot, artifacts)
        self._add_direct_structure(snapshot, file_candidates, symbol_candidates)
        self._add_graph_neighborhood(snapshot, file_candidates, symbol_candidates, budget.max_graph_depth)
        self._add_symbol_files(file_candidates, symbol_candidates, artifacts)
        dependency_candidates = self._dependency_candidates(snapshot, file_candidates, symbol_candidates)

        files, omitted_files = _take_ranked(file_candidates, budget.max_files)
        symbols, omitted_symbols = _take_ranked(symbol_candidates, budget.max_symbols)
        dependencies, omitted_dependencies = _take_ranked(
            dependency_candidates,
            budget.max_dependencies,
        )
        file_refs = tuple(
            FileReference(
                repository_path=path,
                fingerprint=artifacts[path].fingerprint,
                role=_role_for_path(path),
                selection_reason=candidate.reason,
                score=candidate.score,
            )
            for path, candidate in files
        )
        symbol_refs = tuple(
            self._symbol_reference(symbol, candidate)
            for symbol, candidate in symbols
        )
        dependency_refs = tuple(
            DependencyReference(
                source=dependency.source,
                target=dependency.target,
                kind=dependency.kind.value,
                resolved=dependency.resolved,
                selection_reason=candidate.reason,
                score=candidate.score,
            )
            for dependency, candidate in dependencies
        )
        excerpts, excerpt_provenance, omitted_excerpt_reasons = self._excerpts(
            file_refs=file_refs,
            symbol_refs=symbol_refs,
            artifacts=artifacts,
            budget=budget,
            security_policy=security_policy,
            repository_root=snapshot.repository_profile.identity.root,
        )
        provenance = self._provenance(
            snapshot=snapshot,
            files=file_refs,
            symbols=symbol_refs,
            dependencies=dependency_refs,
            excerpts=excerpts,
            excerpt_provenance=excerpt_provenance,
        )
        repository_summary = self._repository_summary(snapshot, budget)
        source_findings = self._source_findings(file_refs, symbol_refs, dependency_refs)
        constrained = self._apply_total_budget(
            repository_summary=repository_summary,
            source_findings=source_findings,
            excerpts=excerpts,
            max_total_characters=budget.max_total_characters,
        )
        repository_summary = constrained.repository_summary
        source_findings = constrained.source_findings
        excerpts = constrained.excerpts
        if constrained.omitted_excerpts:
            omitted_excerpt_reasons["total_context_budget"] += constrained.omitted_excerpts

        omitted_counts = {
            "files": omitted_files,
            "symbols": omitted_symbols,
            "dependencies": omitted_dependencies,
            "source_findings": constrained.omitted_source_findings,
            "excerpts": sum(omitted_excerpt_reasons.values()),
        }
        omission_reasons: dict[str, int] = defaultdict(int)
        if omitted_files:
            omission_reasons["file_limit"] += omitted_files
        if omitted_symbols:
            omission_reasons["symbol_limit"] += omitted_symbols
        if omitted_dependencies:
            omission_reasons["dependency_limit"] += omitted_dependencies
        if constrained.omitted_source_findings:
            omission_reasons["total_context_budget"] += constrained.omitted_source_findings
        for reason, count in omitted_excerpt_reasons.items():
            omission_reasons[reason] += count
        usage = {
            "profile_characters": len(repository_summary),
            "files": len(file_refs),
            "symbols": len(symbol_refs),
            "dependencies": len(dependency_refs),
            "excerpts": len(excerpts),
            "excerpt_characters": sum(len(excerpt.content) for excerpt in excerpts),
            "total_characters": len(repository_summary)
            + sum(len(finding) for finding in source_findings)
            + sum(len(excerpt.content) for excerpt in excerpts),
        }
        configured_limits = {
            "max_profile_characters": budget.max_profile_characters,
            "max_files": budget.max_files,
            "max_symbols": budget.max_symbols,
            "max_dependencies": budget.max_dependencies,
            "max_excerpts": budget.max_excerpts,
            "max_excerpt_lines": budget.max_excerpt_lines,
            "max_excerpt_characters": budget.max_excerpt_characters,
            "max_total_characters": budget.max_total_characters,
            "max_file_bytes": budget.max_file_bytes,
            "max_graph_depth": budget.max_graph_depth,
        }
        truncation = ContextTruncationReport(
            configured_limits=configured_limits,
            actual_usage=usage,
            omitted_counts=omitted_counts,
            omission_reasons=dict(sorted(omission_reasons.items())),
            truncated=any(omitted_counts.values()),
            insufficient=not file_refs,
        )
        projection = {
            "repository_summary": repository_summary,
            "source_findings": source_findings,
            "files": [
                (item.repository_path, item.fingerprint, item.role, item.selection_reason, item.score)
                for item in file_refs
            ],
            "symbols": [
                (
                    item.qualified_name,
                    item.kind,
                    item.module,
                    item.repository_path,
                    item.line_start,
                    item.line_end,
                    item.selection_reason,
                    item.score,
                )
                for item in symbol_refs
            ],
            "dependencies": [
                (item.source, item.target, item.kind, item.resolved, item.selection_reason, item.score)
                for item in dependency_refs
            ],
            "excerpts": [
                (
                    item.repository_path,
                    item.line_start,
                    item.line_end,
                    item.content,
                    item.fingerprint,
                    item.provenance_id,
                )
                for item in excerpts
            ],
            "provenance": [
                (
                    item.provenance_id,
                    item.kind,
                    item.subject,
                    item.source_fingerprint,
                    item.selection_reason,
                    item.location_path,
                    item.line_start,
                    item.line_end,
                    item.derivation,
                    item.resolution_confidence,
                    item.sensitivity_action,
                )
                for item in provenance
            ],
            "truncation": {
                "configured_limits": dict(truncation.configured_limits),
                "actual_usage": dict(truncation.actual_usage),
                "omitted_counts": dict(truncation.omitted_counts),
                "omission_reasons": dict(truncation.omission_reasons),
                "truncated": truncation.truncated,
                "insufficient": truncation.insufficient,
            },
        }
        return SelectedRepositoryContext(
            repository_summary=repository_summary,
            source_findings=source_findings,
            files=file_refs,
            symbols=symbol_refs,
            dependencies=dependency_refs,
            excerpts=excerpts,
            provenance=provenance,
            truncation=truncation,
            context_fingerprint=context_fingerprint(
                repository_snapshot=snapshot.snapshot_fingerprint,
                budget=budget,
                projection=projection,
            ),
        )

    def _file_candidates(
        self,
        goal_lower: str,
        tokens: frozenset[str],
        artifacts: dict[str, SourceArtifactRecord],
    ) -> dict[str, _Candidate]:
        candidates: dict[str, _Candidate] = {}
        for path, _artifact in artifacts.items():
            path_lower = path.lower()
            stem_tokens = _goal_tokens(PurePosixPath(path_lower).stem)
            score = 0
            reason = "broad_lexical_fallback"
            if path_lower in goal_lower:
                score, reason = 1_000, "exact_goal_path_match"
            elif stem_tokens and stem_tokens.issubset(tokens):
                score, reason = 850, "exact_goal_path_match"
            elif stem_tokens & tokens:
                score, reason = 250, "broad_lexical_fallback"
            if _role_for_path(path) == "test" and (stem_tokens & tokens or "test" in tokens):
                score, reason = max(score, 700), "contract_test_evidence"
            if score:
                candidates[path] = _Candidate(score=score, reason=reason)
        return candidates

    def _symbol_candidates(
        self,
        goal_lower: str,
        tokens: frozenset[str],
        snapshot: RepositoryContextSnapshot,
        artifacts: dict[str, SourceArtifactRecord],
    ) -> dict[Symbol, _Candidate]:
        candidates: dict[Symbol, _Candidate] = {}
        allowed_paths = set(artifacts)
        for symbol in snapshot.index.symbols:
            path = symbol.location.path.as_posix()
            if path not in allowed_paths:
                continue
            qualified = symbol.identity.qualified_name.lower()
            name_tokens = _goal_tokens(qualified.split(".")[-1])
            module_tokens = _goal_tokens(symbol.identity.module.lower())
            if qualified in goal_lower:
                candidates[symbol] = _Candidate(1_000, "exact_goal_symbol_match")
            elif name_tokens and name_tokens.issubset(tokens):
                candidates[symbol] = _Candidate(900, "exact_goal_symbol_match")
            elif module_tokens and module_tokens.issubset(tokens):
                candidates[symbol] = _Candidate(750, "exact_goal_path_match")
            elif name_tokens & tokens:
                candidates[symbol] = _Candidate(300, "broad_lexical_fallback")
        return candidates

    def _add_direct_structure(
        self,
        snapshot: RepositoryContextSnapshot,
        files: dict[str, _Candidate],
        symbols: dict[Symbol, _Candidate],
    ) -> None:
        target_modules = {symbol.identity.module for symbol in symbols}
        target_modules.update(PurePosixPath(path).with_suffix("").as_posix().replace("/", ".") for path in files)
        for dependency in snapshot.index.dependencies:
            if dependency.source in target_modules or dependency.target in target_modules:
                for symbol in snapshot.index.symbols:
                    if symbol.identity.module in {dependency.source, dependency.target}:
                        existing = symbols.get(symbol)
                        candidate = _Candidate(600, "direct_structure")
                        if existing is None or candidate.score > existing.score:
                            symbols[symbol] = candidate

    def _add_graph_neighborhood(
        self,
        snapshot: RepositoryContextSnapshot,
        files: dict[str, _Candidate],
        symbols: dict[Symbol, _Candidate],
        max_depth: int,
    ) -> None:
        if snapshot.graph is None or max_depth == 0:
            return
        graph = snapshot.graph.graph
        targeted = {symbol.identity.qualified_name for symbol in symbols}
        targeted.update(symbol.identity.module for symbol in symbols)
        selected_node_ids = {
            node.id
            for node in graph.nodes
            if node.qualified_name in targeted or node.name in targeted
        }
        frontier = set(selected_node_ids)
        visited = set(selected_node_ids)
        for _ in range(max_depth):
            next_frontier: set[str] = set()
            for edge in graph.edges:
                if edge.source in frontier:
                    next_frontier.add(edge.target)
                if edge.target in frontier:
                    next_frontier.add(edge.source)
            next_frontier.difference_update(visited)
            if not next_frontier:
                break
            visited.update(next_frontier)
            frontier = next_frontier
        related_names = {
            node.qualified_name
            for node in graph.nodes
            if node.id in visited and node.id not in selected_node_ids
        }
        for symbol in snapshot.index.symbols:
            if symbol.identity.qualified_name in related_names:
                existing = symbols.get(symbol)
                candidate = _Candidate(450, "impact_expansion")
                if existing is None or candidate.score > existing.score:
                    symbols[symbol] = candidate

    @staticmethod
    def _add_symbol_files(
        files: dict[str, _Candidate],
        symbols: dict[Symbol, _Candidate],
        artifacts: dict[str, SourceArtifactRecord],
    ) -> None:
        """Ensure selected structural symbols bring their actual root-relative file evidence."""
        for symbol, candidate in symbols.items():
            path = symbol.location.path.as_posix()
            if path not in artifacts:
                continue
            existing = files.get(path)
            if existing is None or candidate.score > existing.score:
                files[path] = _Candidate(candidate.score, candidate.reason)

    def _dependency_candidates(
        self,
        snapshot: RepositoryContextSnapshot,
        files: dict[str, _Candidate],
        symbols: dict[Symbol, _Candidate],
    ) -> dict[Dependency, _Candidate]:
        candidates: dict[Dependency, _Candidate] = {}
        target_modules = {symbol.identity.module for symbol in symbols}
        target_modules.update(PurePosixPath(path).with_suffix("").as_posix().replace("/", ".") for path in files)
        for dependency in snapshot.index.dependencies:
            if dependency.source in target_modules or dependency.target in target_modules:
                candidates[dependency] = _Candidate(600, "direct_structure")
        return candidates

    def _symbol_reference(self, symbol: Symbol, candidate: _Candidate) -> SymbolReference:
        return SymbolReference(
            qualified_name=symbol.identity.qualified_name,
            kind=symbol.identity.kind.value,
            module=symbol.identity.module,
            repository_path=symbol.location.path.as_posix(),
            line_start=symbol.location.line,
            line_end=symbol.location.end_line,
            selection_reason=candidate.reason,
            score=candidate.score,
        )

    def _excerpts(
        self,
        *,
        file_refs: tuple[FileReference, ...],
        symbol_refs: tuple[SymbolReference, ...],
        artifacts: dict[str, SourceArtifactRecord],
        budget: ContextBudget,
        security_policy: ContextSecurityPolicy,
        repository_root: Path,
    ) -> tuple[tuple[SourceExcerpt, ...], tuple[ContextProvenanceRecord, ...], defaultdict[str, int]]:
        excerpts: list[SourceExcerpt] = []
        provenance: list[ContextProvenanceRecord] = []
        omissions: defaultdict[str, int] = defaultdict(int)
        symbols_by_path: dict[str, list[SymbolReference]] = defaultdict(list)
        for symbol in symbol_refs:
            symbols_by_path[symbol.repository_path].append(symbol)
        for file_ref in file_refs:
            if len(excerpts) >= budget.max_excerpts:
                omissions["excerpt_limit"] += 1
                continue
            artifact = artifacts[file_ref.repository_path]
            sanitized = security_policy.read_sanitized(
                artifact.analysis.identity.absolute_path,
                repository_root,
            )
            if sanitized.content is None:
                omissions[sanitized.decision.reason] += 1
                continue
            anchor = min(
                (symbol.line_start for symbol in symbols_by_path[file_ref.repository_path]),
                default=1,
            )
            lines = sanitized.content.splitlines()
            start = max(anchor - 1, 0)
            end = min(start + budget.max_excerpt_lines, len(lines))
            content = "\n".join(lines[start:end])
            if len(content) > budget.max_excerpt_characters:
                content = content[: budget.max_excerpt_characters]
                omissions["excerpt_character_limit"] += 1
            provenance_id = f"excerpt:{file_ref.repository_path}:{start + 1}-{max(end, start + 1)}"
            excerpts.append(
                SourceExcerpt(
                    repository_path=file_ref.repository_path,
                    line_start=start + 1,
                    line_end=max(end, start + 1),
                    content=content,
                    fingerprint=file_ref.fingerprint,
                    provenance_id=provenance_id,
                )
            )
            provenance.append(
                ContextProvenanceRecord(
                    provenance_id=provenance_id,
                    kind="file_excerpt",
                    subject=file_ref.repository_path,
                    source_fingerprint=file_ref.fingerprint,
                    selection_reason=file_ref.selection_reason,
                    location_path=file_ref.repository_path,
                    line_start=start + 1,
                    line_end=max(end, start + 1),
                    derivation="context_selector_excerpt_v1",
                    sensitivity_action=sanitized.decision.action,
                )
            )
        return tuple(excerpts), tuple(provenance), omissions

    def _provenance(
        self,
        *,
        snapshot: RepositoryContextSnapshot,
        files: tuple[FileReference, ...],
        symbols: tuple[SymbolReference, ...],
        dependencies: tuple[DependencyReference, ...],
        excerpts: tuple[SourceExcerpt, ...],
        excerpt_provenance: tuple[ContextProvenanceRecord, ...],
    ) -> tuple[ContextProvenanceRecord, ...]:
        records: list[ContextProvenanceRecord] = [
            ContextProvenanceRecord(
                provenance_id="repository:profile",
                kind="repository_profile",
                subject=snapshot.repository_profile.identity.name,
                source_fingerprint=snapshot.snapshot_fingerprint.value,
                selection_reason="repository_constraints",
                derivation="RepositoryRuntime.scan",
            ),
            ContextProvenanceRecord(
                provenance_id="repository:state",
                kind="git_state",
                subject="repository_state",
                source_fingerprint=snapshot.repository_state.state_fingerprint,
                selection_reason="repository_constraints",
                derivation="VcsReadFacade.snapshot",
            ),
        ]
        records.extend(
            ContextProvenanceRecord(
                provenance_id=f"file:{item.repository_path}",
                kind="source_analysis",
                subject=item.repository_path,
                source_fingerprint=item.fingerprint,
                selection_reason=item.selection_reason,
                location_path=item.repository_path,
                derivation="SourceRuntime.analyze_file",
            )
            for item in files
        )
        records.extend(
            ContextProvenanceRecord(
                provenance_id=f"symbol:{item.qualified_name}",
                kind="index",
                subject=item.qualified_name,
                source_fingerprint=next(
                    file_item.fingerprint
                    for file_item in files
                    if file_item.repository_path == item.repository_path
                ),
                selection_reason=item.selection_reason,
                location_path=item.repository_path,
                line_start=item.line_start,
                line_end=item.line_end,
                derivation="IndexRuntime.build",
            )
            for item in symbols
            if any(file_item.repository_path == item.repository_path for file_item in files)
        )
        records.extend(
            ContextProvenanceRecord(
                provenance_id=f"dependency:{item.source}->{item.target}",
                kind="graph_query",
                subject=f"{item.source}->{item.target}",
                source_fingerprint=snapshot.snapshot_fingerprint.value,
                selection_reason=item.selection_reason,
                derivation="GraphRuntime.build",
                resolution_confidence="exact" if item.resolved else "unresolved",
            )
            for item in dependencies
        )
        records.extend(excerpt_provenance)
        return tuple(sorted(records, key=lambda item: item.provenance_id))

    @staticmethod
    def _repository_summary(snapshot: RepositoryContextSnapshot, budget: ContextBudget) -> str:
        profile = snapshot.repository_profile
        capabilities = [
            name
            for name, available in (
                ("git", profile.capabilities.git),
                ("tests", profile.capabilities.tests),
                ("ci", profile.capabilities.ci),
                ("type_checking", profile.capabilities.type_checking),
                ("linting", profile.capabilities.linting),
            )
            if available
        ]
        summary = (
            f"Repository {profile.identity.name}; kind={profile.kind.value}; layout={profile.layout.value}; "
            f"files={profile.statistics.files}; tests={profile.statistics.tests}; "
            f"languages={','.join(item.language for item in profile.statistics.languages)}; "
            f"capabilities={','.join(capabilities) or 'none'}; "
            f"vcs={'available' if snapshot.repository_state.available else 'unavailable'}; "
            f"snapshot={snapshot.snapshot_fingerprint.value[:16]}."
        )
        return summary[: budget.max_profile_characters]

    @staticmethod
    def _source_findings(
        files: tuple[FileReference, ...],
        symbols: tuple[SymbolReference, ...],
        dependencies: tuple[DependencyReference, ...],
    ) -> tuple[str, ...]:
        findings = [
            f"selected_file path={item.repository_path} role={item.role} reason={item.selection_reason}"
            for item in files
        ]
        findings.extend(
            f"selected_symbol name={item.qualified_name} path={item.repository_path} lines={item.line_start}-{item.line_end} reason={item.selection_reason}"
            for item in symbols
        )
        findings.extend(
            f"selected_dependency source={item.source} target={item.target} kind={item.kind} resolved={item.resolved}"
            for item in dependencies
        )
        return tuple(findings)

    @staticmethod
    def _apply_total_budget(
        *,
        repository_summary: str,
        source_findings: tuple[str, ...],
        excerpts: tuple[SourceExcerpt, ...],
        max_total_characters: int,
    ) -> _BudgetedProjection:
        summary_limit = min(len(repository_summary), max_total_characters // 4)
        bounded_summary = repository_summary[:summary_limit]
        used = len(bounded_summary)
        retained_findings: list[str] = []
        omitted_findings = 0
        for finding in source_findings:
            if used + len(finding) > max_total_characters:
                omitted_findings += 1
                continue
            retained_findings.append(finding)
            used += len(finding)
        retained_excerpts: list[SourceExcerpt] = []
        omitted_excerpts = 0
        for excerpt in excerpts:
            if used + len(excerpt.content) > max_total_characters:
                omitted_excerpts += 1
                continue
            retained_excerpts.append(excerpt)
            used += len(excerpt.content)
        return _BudgetedProjection(
            repository_summary=bounded_summary,
            source_findings=tuple(retained_findings),
            excerpts=tuple(retained_excerpts),
            omitted_source_findings=omitted_findings,
            omitted_excerpts=omitted_excerpts,
        )


@dataclass(frozen=True, slots=True)
class _BudgetedProjection:
    repository_summary: str
    source_findings: tuple[str, ...]
    excerpts: tuple[SourceExcerpt, ...]
    omitted_source_findings: int
    omitted_excerpts: int


def _goal_tokens(value: str) -> frozenset[str]:
    return frozenset(token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1)


def _role_for_path(path: str) -> str:
    parts = tuple(part.lower() for part in PurePosixPath(path).parts)
    name = parts[-1]
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if name in {"__init__.py", "main.py", "app.py"}:
        return "entrypoint"
    return "source"


def _take_ranked[T](candidates: dict[T, _Candidate], limit: int) -> tuple[tuple[tuple[T, _Candidate], ...], int]:
    ranked = tuple(
        sorted(
            candidates.items(),
            key=lambda item: (-item[1].score, item[1].reason, _candidate_key(item[0])),
        )
    )
    return ranked[:limit], max(len(ranked) - limit, 0)


def _candidate_key(candidate: object) -> str:
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, Symbol):
        return candidate.identity.qualified_name
    if isinstance(candidate, Dependency):
        return f"{candidate.source}->{candidate.target}:{candidate.kind.value}"
    return str(candidate)
