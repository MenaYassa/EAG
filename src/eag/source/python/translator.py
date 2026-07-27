import hashlib
from pathlib import Path, PurePosixPath

from eag.source.metrics import AnalysisMetrics
from eag.source.models import (
    AnalysisResult,
    Dependency,
    DependencyKind,
    Documentation,
    Language,
    ModuleIdentity,
    SourceFileIdentity,
    SourceLocation,
    Symbol,
    SymbolIdentity,
    SymbolKind,
    Visibility,
)
from eag.source.python.models import PythonClass, PythonFunction, PythonImport, PythonModule


class PythonTranslator:
    def translate(
        self,
        file_path: Path,
        repo_root: Path,
        module: PythonModule,
        lines: list[str],
    ) -> AnalysisResult:
        fingerprint = hashlib.sha256(
            f"{file_path.stat().st_mtime}:{file_path.stat().st_size}".encode()
        ).hexdigest()

        identity = SourceFileIdentity(
            absolute_path=file_path.resolve(),
            repository_path=PurePosixPath(file_path.resolve().relative_to(repo_root.resolve())),
            language=Language.PYTHON,
            fingerprint=fingerprint,
        )

        module_identity = ModuleIdentity(
            name=module.name,
            path=PurePosixPath(file_path.resolve().relative_to(repo_root.resolve())),
        )

        symbols = self._translate_symbols(module)
        dependencies = self._translate_imports(module.name, module.imports)
        metrics = self._calculate_metrics(lines, symbols, dependencies)

        return AnalysisResult(
            identity=identity,
            module=module_identity,
            symbols=symbols,
            dependencies=dependencies,
            metrics=metrics,
            semantic_relationships=module.semantic_relationships,  # ADD THIS LINE
        )

    def _translate_symbols(self, module: PythonModule) -> tuple[Symbol, ...]:
        symbols: list[Symbol] = []

        for func in module.functions:
            symbols.append(self._translate_function(func, module.name, is_method=False))

        for cls in module.classes:
            symbols.append(self._translate_class(cls, module.name))
            for method in cls.methods:
                symbols.append(
                    self._translate_function(method, module.name, is_method=True, parent=cls.name)
                )

        return tuple(symbols)

    def _translate_function(
        self, func: PythonFunction, module_name: str, is_method: bool, parent: str | None = None
    ) -> Symbol:
        parts = [module_name, parent, func.name]
        qualified_name = ".".join(p for p in parts if p)

        kind = SymbolKind.METHOD if is_method else SymbolKind.FUNCTION
        visibility = self._determine_visibility(func.name)

        attributes = set()
        if func.is_async:
            attributes.add("is_async")
        for dec in func.decorators:
            if dec == "staticmethod":
                attributes.add("is_static")
            if dec == "classmethod":
                attributes.add("is_class")
            if dec == "property":
                attributes.add("is_property")
            if dec == "abstractmethod":
                attributes.add("is_abstract")

        return Symbol(
            identity=SymbolIdentity(qualified_name=qualified_name, module=module_name, kind=kind),
            location=SourceLocation(
                path=PurePosixPath(module_name.replace(".", "/") + ".py"),
                line=func.line,
                column=func.col,
                end_line=func.line,
                end_column=func.col,
            ),
            visibility=visibility,
            documentation=Documentation(
                summary=func.docstring.split("\n")[0] if func.docstring else "",
                raw=func.docstring or "",
            ),
            attributes=frozenset(attributes),
        )

    def _translate_class(self, cls: PythonClass, module_name: str) -> Symbol:
        qualified_name = f"{module_name}.{cls.name}"
        visibility = self._determine_visibility(cls.name)

        attributes = set()
        for dec in cls.decorators:
            if dec == "dataclass":
                attributes.add("is_dataclass")
        for base in cls.bases:
            if base == "Protocol":
                attributes.add("is_protocol")
            if base == "Enum":
                attributes.add("is_enum")

        return Symbol(
            identity=SymbolIdentity(
                qualified_name=qualified_name, module=module_name, kind=SymbolKind.CLASS
            ),
            location=SourceLocation(
                path=PurePosixPath(module_name.replace(".", "/") + ".py"),
                line=cls.line,
                column=cls.col,
                end_line=cls.line,
                end_column=cls.col,
            ),
            visibility=visibility,
            documentation=Documentation(
                summary=cls.docstring.split("\n")[0] if cls.docstring else "",
                raw=cls.docstring or "",
            ),
            attributes=frozenset(attributes),
        )

    def _translate_imports(
        self, module_name: str, imports: tuple[PythonImport, ...]
    ) -> tuple[Dependency, ...]:
        deps: list[Dependency] = []
        for imp in imports:
            target = f"{imp.module}.{imp.symbol}" if imp.symbol else imp.module
            if imp.relative_level > 0:
                target = f"{'.' * imp.relative_level}{target}"
            deps.append(
                Dependency(
                    source=module_name,
                    target=target,
                    kind=DependencyKind.IMPORT,
                )
            )
        return tuple(deps)

    def _determine_visibility(self, name: str) -> Visibility:
        if name.startswith("__") and name.endswith("__"):
            return Visibility.PUBLIC
        if name.startswith("__"):
            return Visibility.PRIVATE
        if name.startswith("_"):
            return Visibility.PROTECTED
        return Visibility.PUBLIC

    def _calculate_metrics(
        self, lines: list[str], symbols: tuple[Symbol, ...], deps: tuple[Dependency, ...]
    ) -> AnalysisMetrics:
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))

        return AnalysisMetrics(
            lines=len(lines),
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            symbols=len(symbols),
            dependencies=len(deps),
        )
