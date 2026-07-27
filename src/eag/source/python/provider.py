"""Python source provider for EAG."""

import ast
import hashlib
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from eag.source.models import (
    Diagnostic,
    DiagnosticSeverity,
    EngineeringSymbol,
    ImportModel,
    Language,
    Location,
    SourceDocument,
    SymbolKind,
    SymbolReference,
    SymbolVisibility,
)


class PythonSymbolVisitor(ast.NodeVisitor):
    """AST Visitor that extracts symbols and resolves references via lexical scoping."""

    def __init__(self, content: str) -> None:
        self.symbols: list[EngineeringSymbol] = []
        self.references: list[SymbolReference] = []
        self._scope: list[str] = []
        self._scopes: list[dict[str, str]] = [{}]
        self._import_map: dict[str, str] = {}
        self._inferred_types: dict[str, str] = {}
        self._class_stack: list[str] = []
        self._class_bases: list[list[str]] = []
        self._source_lines = content.splitlines(keepends=True)

    def _qname(self, name: str) -> str:
        return ".".join(self._scope + [name]) if self._scope else name

    def _resolve_name(self, name: str) -> str | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        if name in self._import_map:
            return self._import_map[name]
        return None

    def _get_visibility(self, name: str) -> SymbolVisibility:
        if name.startswith("__") and name.endswith("__"):
            return SymbolVisibility.PUBLIC
        if name.startswith("__"):
            return SymbolVisibility.PRIVATE
        if name.startswith("_"):
            return SymbolVisibility.PROTECTED
        return SymbolVisibility.PUBLIC

    def _get_decorator_name(self, d: ast.AST) -> str:
        if isinstance(d, ast.Name):
            return d.id
        if isinstance(d, ast.Attribute):
            return d.attr
        if isinstance(d, ast.Call):
            return self._get_decorator_name(d.func)
        return "unknown"

    def _is_generator(self, node: ast.AST) -> bool:
        return any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))

    def _find_name_col(self, line: int, start_col: int, name: str) -> int:
        if line < 1 or line > len(self._source_lines):
            return start_col
        idx = self._source_lines[line - 1].find(name, start_col)
        return idx if idx != -1 else start_col

    def _make_loc(self, node: ast.AST, name: str | None = None) -> Location:
        lineno = int(getattr(node, "lineno", 0))
        col_offset = int(getattr(node, "col_offset", 0))
        end_lineno = int(getattr(node, "end_lineno", lineno))
        end_col_offset = int(getattr(node, "end_col_offset", col_offset))

        col = col_offset
        if name:
            col = self._find_name_col(lineno, col_offset, name)

        return Location(
            line=lineno,
            column=col,
            end_line=end_lineno,
            end_column=end_col_offset,
        )

    def _make_attr_loc(self, node: ast.Attribute) -> Location:
        end_col = int(getattr(node, "end_col_offset", getattr(node, "col_offset", 0)))
        start_col = end_col - len(node.attr)
        line = int(getattr(node, "end_lineno", getattr(node, "lineno", 0)))
        return Location(
            line=line,
            column=start_col,
            end_line=line,
            end_column=end_col,
        )

    def _infer_type(self, value: ast.AST) -> str | None:
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name):
                return self._resolve_name(value.func.id) or value.func.id
            elif isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
                base = self._resolve_name(value.func.value.id) or value.func.value.id
                return f"{base}.{value.func.attr}"
        return None

    def visit_Assign(self, node: ast.Assign) -> None:
        inferred = self._infer_type(node.value)
        if inferred:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    qname = self._qname(target.id)
                    self._inferred_types[qname] = inferred
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and isinstance(node.annotation, ast.Name):
            qname = self._qname(node.target.id)
            self._inferred_types[qname] = (
                self._resolve_name(node.annotation.id) or node.annotation.id
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self._import_map[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            self._import_map[name] = f"{module}.{alias.name}" if module else alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qname = self._qname(node.name)
        self.symbols.append(
            EngineeringSymbol(
                id=qname,
                name=node.name,
                qualified_name=qname,
                kind=SymbolKind.CLASS,
                visibility=self._get_visibility(node.name),
                location=self._make_loc(node, node.name),
                parent=".".join(self._scope) if self._scope else None,
                decorators=tuple(self._get_decorator_name(d) for d in node.decorator_list),
            )
        )
        self._scopes[-1][node.name] = qname

        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        self._class_bases.append(bases)

        self._scope.append(node.name)
        self._class_stack.append(node.name)
        self._scopes.append({"self": qname, "cls": qname})
        self.generic_visit(node)
        self._scopes.pop()
        self._class_stack.pop()
        self._scope.pop()
        self._class_bases.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        qname = self._qname(node.name)
        self.symbols.append(
            EngineeringSymbol(
                id=qname,
                name=node.name,
                qualified_name=qname,
                kind=SymbolKind.METHOD if self._class_stack else SymbolKind.FUNCTION,
                visibility=self._get_visibility(node.name),
                location=self._make_loc(node, node.name),
                parent=".".join(self._scope) if self._scope else None,
                is_async=is_async,
                is_generator=self._is_generator(node),
                decorators=tuple(self._get_decorator_name(d) for d in node.decorator_list),
            )
        )
        self._scopes[-1][node.name] = qname
        self._scope.append(node.name)

        func_scope: dict[str, str] = {}
        all_args = node.args.args + node.args.kwonlyargs + getattr(node.args, "posonlyargs", [])
        for arg in all_args:
            if arg.arg != "self" and arg.arg != "cls":
                arg_qname = self._qname(arg.arg)
                func_scope[arg.arg] = arg_qname
                self.symbols.append(
                    EngineeringSymbol(
                        id=arg_qname,
                        name=arg.arg,
                        qualified_name=arg_qname,
                        kind=SymbolKind.VARIABLE,
                        location=self._make_loc(arg, arg.arg),
                    )
                )
        if node.args.vararg:
            func_scope[node.args.vararg.arg] = self._qname(node.args.vararg.arg)
        if node.args.kwarg:
            func_scope[node.args.kwarg.arg] = self._qname(node.args.kwarg.arg)

        self._scopes.append(func_scope)
        self.generic_visit(node)
        self._scopes.pop()
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._scope.append("<lambda>")
        lambda_scope: dict[str, str] = {}
        all_args = node.args.args + node.args.kwonlyargs + getattr(node.args, "posonlyargs", [])
        for arg in all_args:
            qname = self._qname(arg.arg)
            lambda_scope[arg.arg] = qname
            self.symbols.append(
                EngineeringSymbol(
                    id=qname,
                    name=arg.arg,
                    qualified_name=qname,
                    kind=SymbolKind.VARIABLE,
                    location=self._make_loc(arg, arg.arg),
                )
            )
        self._scopes.append(lambda_scope)
        self.generic_visit(node)
        self._scopes.pop()
        self._scope.pop()

    def _bind_target(self, node: ast.AST, scope: dict[str, str]) -> None:
        if isinstance(node, ast.Name):
            qname = self._qname(node.id)
            scope[node.id] = qname
            self.symbols.append(
                EngineeringSymbol(
                    id=qname,
                    name=node.id,
                    qualified_name=qname,
                    kind=SymbolKind.VARIABLE,
                    location=self._make_loc(node),
                )
            )
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._bind_target(elt, scope)

    def _visit_comp(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        self._scope.append("<local>")
        comp_scope: dict[str, str] = {}
        self.visit(node.generators[0].iter)
        self._bind_target(node.generators[0].target, comp_scope)
        self._scopes.append(comp_scope)

        for gen in node.generators[1:]:
            self.visit(gen.iter)
            self._bind_target(gen.target, self._scopes[-1])
            for if_ in gen.ifs:
                self.visit(if_)

        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)

        self._scopes.pop()
        self._scope.pop()

    visit_ListComp = _visit_comp
    visit_SetComp = _visit_comp
    visit_DictComp = _visit_comp
    visit_GeneratorExp = _visit_comp

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self._scope.append("<local>")
            qname = self._qname(node.name)
            self._scope.pop()

            col = self._find_name_col(node.lineno, getattr(node, "col_offset", 0), node.name)
            self._scopes[-1][node.name] = qname
            self.symbols.append(
                EngineeringSymbol(
                    id=qname,
                    name=node.name,
                    qualified_name=qname,
                    kind=SymbolKind.VARIABLE,
                    location=Location(line=node.lineno, column=col),
                )
            )
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self._scope.append("<local>")
            qname = self._qname(node.name)
            self._scope.pop()

            col = self._find_name_col(node.lineno, getattr(node, "col_offset", 0), node.name)
            self._scopes[-1][node.name] = qname
            self.symbols.append(
                EngineeringSymbol(
                    id=qname,
                    name=node.name,
                    qualified_name=qname,
                    kind=SymbolKind.VARIABLE,
                    location=Location(line=node.lineno, column=col),
                )
            )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            resolved = self._resolve_name(node.id)
            target = resolved if resolved else node.id
            self.references.append(
                SymbolReference(
                    source=".".join(self._scope) if self._scope else "module",
                    target=target,
                    line=node.lineno,
                    column=node.col_offset,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    end_col=getattr(node, "end_col_offset", node.col_offset),
                )
            )
        elif isinstance(node.ctx, ast.Store):
            qname = self._qname(node.id)
            self._scopes[-1][node.id] = qname
            self.symbols.append(
                EngineeringSymbol(
                    id=qname,
                    name=node.id,
                    qualified_name=qname,
                    kind=SymbolKind.VARIABLE,
                    location=self._make_loc(node),
                )
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "super"
            ):
                if self._class_bases and self._scope:
                    base = self._class_bases[-1][0] if self._class_bases[-1] else None
                    if base:
                        target = f"{base}.{node.attr}"
                        loc = self._make_attr_loc(node)
                        self.references.append(
                            SymbolReference(
                                source=".".join(self._scope) if self._scope else "module",
                                target=target,
                                line=loc.line,
                                column=loc.column,
                                end_line=loc.end_line,
                                end_col=loc.end_column,
                            )
                        )
            elif isinstance(node.value, ast.Name):
                base_qname = self._qname(node.value.id)
                resolved_base = self._resolve_name(node.value.id)

                if base_qname in self._inferred_types:
                    target = f"{self._inferred_types[base_qname]}.{node.attr}"
                elif resolved_base:
                    target = f"{resolved_base}.{node.attr}"
                else:
                    target = f"{node.value.id}.{node.attr}"

                loc = self._make_attr_loc(node)
                self.references.append(
                    SymbolReference(
                        source=".".join(self._scope) if self._scope else "module",
                        target=target,
                        line=loc.line,
                        column=loc.column,
                        end_line=loc.end_line,
                        end_col=loc.end_column,
                    )
                )
            else:
                loc = self._make_attr_loc(node)
                self.references.append(
                    SymbolReference(
                        source=".".join(self._scope) if self._scope else "module",
                        target=node.attr,
                        line=loc.line,
                        column=loc.column,
                        end_line=loc.end_line,
                        end_col=loc.end_column,
                    )
                )
        self.generic_visit(node)


class PythonSourceProvider:
    """Concrete SourceProvider implementation using Python's ast module."""

    @property
    def language(self) -> Language:
        return Language.PYTHON

    def supports(self, path: Path) -> bool:
        return path.suffix == ".py"

    def parse(self, path: Path, content: str) -> SourceDocument:
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

        try:
            tree = ast.parse(content, filename=str(path))
            diagnostics: list[Diagnostic] = []
        except SyntaxError as e:
            return SourceDocument(
                path=path,
                language=Language.PYTHON,
                checksum=checksum,
                diagnostics=(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        message=str(e),
                        location=Location(line=e.lineno or 0, column=e.offset or 0),
                        rule="syntax-error",
                        provider="python",
                    ),
                ),
            )

        visitor = PythonSymbolVisitor(content)
        visitor.visit(tree)

        defined_qnames = {s.qualified_name for s in visitor.symbols}
        ref_map: dict[str, list[SymbolReference]] = defaultdict(list)
        for ref in visitor.references:
            if ref.target in defined_qnames:
                ref_map[ref.target].append(ref)

        final_symbols = []
        for sym in visitor.symbols:
            final_symbols.append(replace(sym, references=tuple(ref_map.get(sym.id, []))))

        used_names = {r.target.split(".")[-1] for r in visitor.references}
        used_names.update({s.name for s in final_symbols})
        imports = self._extract_imports(tree, used_names)

        return SourceDocument(
            path=path,
            language=Language.PYTHON,
            checksum=checksum,
            symbols=tuple(final_symbols),
            imports=tuple(imports),
            references=tuple(visitor.references),
            diagnostics=tuple(diagnostics),
        )

    def _extract_imports(self, tree: ast.Module, used_names: set[str]) -> list[ImportModel]:
        imports: list[ImportModel] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    check_name = alias.asname or alias.name.split(".")[0]
                    imports.append(
                        ImportModel(
                            module=alias.name,
                            alias=alias.asname,
                            used=check_name in used_names,
                            location=Location(
                                line=getattr(alias, "lineno", getattr(node, "lineno", 0)),
                                column=getattr(alias, "col_offset", getattr(node, "col_offset", 0)),
                            ),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    check_name = alias.asname or alias.name
                    imports.append(
                        ImportModel(
                            module=module,
                            name=alias.name,
                            alias=alias.asname,
                            relative=bool(node.level),
                            used=check_name in used_names,
                            location=Location(
                                line=getattr(alias, "lineno", getattr(node, "lineno", 0)),
                                column=getattr(alias, "col_offset", getattr(node, "col_offset", 0)),
                            ),
                        )
                    )
        return imports

    def validate(self, document: SourceDocument) -> tuple[Diagnostic, ...]:
        return document.diagnostics
