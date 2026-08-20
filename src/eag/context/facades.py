"""Read-only adapters over existing repository contracts for G2.2."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from eag.context.models import RepositoryStateEvidence
from eag.context.sensitivity import ContextSecurityPolicy, SensitivityDecision
from eag.repository.models import RepositoryProfile
from eag.repository.runtime import RepositoryRuntime as DiscoveryRepositoryRuntime


@runtime_checkable
class VcsReadFacade(Protocol):
    """A deliberately narrow, non-executing VCS-state boundary for context assembly."""

    def snapshot(self) -> RepositoryStateEvidence: ...


class UnavailableVcsReadFacade:
    """No-VCS implementation for plain directories and zero-effect benchmark fixtures."""

    def snapshot(self) -> RepositoryStateEvidence:
        return RepositoryStateEvidence(available=False, state_fingerprint="no_vcs")


class ProvidedVcsReadFacade:
    """Returns VCS state captured by an outer authorized read integration without invoking it."""

    def __init__(self, evidence: RepositoryStateEvidence) -> None:
        self._evidence = evidence

    def snapshot(self) -> RepositoryStateEvidence:
        return self._evidence


class RepositoryDiscoveryFacade:
    """A read-only adapter over existing RepositoryRuntime scan/profile functionality."""

    def __init__(
        self,
        runtime: DiscoveryRepositoryRuntime,
        repository_root: Path,
        security_policy: ContextSecurityPolicy,
    ) -> None:
        self._runtime = runtime
        self._root = repository_root.resolve()
        self._security_policy = security_policy

    @property
    def root(self) -> Path:
        return self._root

    def profile(self) -> RepositoryProfile:
        """Return a fresh profile from the existing scanner-backed runtime."""
        return self._runtime.scan(self._root).profile

    def source_candidates(self, supported_extensions: tuple[str, ...]) -> tuple[Path, ...]:
        """Return safe, supported, deterministic source paths without reading content."""
        extensions = frozenset(extension.lower() for extension in supported_extensions)
        candidates: list[Path] = []
        try:
            for path in self._root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                decision = self._security_policy.classify_path(path, self._root)
                if decision.action != "excluded":
                    candidates.append(path)
        except OSError:
            # Profile scan reports detailed discovery failures. Safe candidate discovery fails closed.
            return ()
        return tuple(sorted(candidates, key=lambda item: item.relative_to(self._root).as_posix()))

    def classify(self, path: Path) -> SensitivityDecision:
        return self._security_policy.classify_path(path, self._root)
