import sys
from enum import StrEnum

from eag.graph.models import GraphNode


class DependencyCategory(StrEnum):
    INTERNAL = "internal"
    STDLIB = "stdlib"
    THIRD_PARTY = "third_party"
    TEST = "test"


class DependencyClassifier:
    def __init__(self, internal_prefixes: set[str] | None = None) -> None:
        self._stdlib = set(sys.stdlib_module_names)
        self._test = {"pytest", "unittest", "mock", "tox", "nox", "coverage"}
        self._internal = internal_prefixes or {"eag", "tests"}

    def classify(self, name: str) -> DependencyCategory:
        root = name.split(".")[0]
        if root in self._test:
            return DependencyCategory.TEST
        if any(name.startswith(p) for p in self._internal):
            return DependencyCategory.INTERNAL
        if root in self._stdlib:
            return DependencyCategory.STDLIB
        return DependencyCategory.THIRD_PARTY

    def group(self, deps: list[GraphNode]) -> dict[DependencyCategory, list[GraphNode]]:
        groups: dict[DependencyCategory, list[GraphNode]] = {cat: [] for cat in DependencyCategory}
        for dep in deps:
            cat = self.classify(dep.qualified_name)
            groups[cat].append(dep)
        return groups
