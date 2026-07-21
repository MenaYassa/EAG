"""AST Rename Visitor for EAG."""

import ast

from eag.source.models import SourceDocument
from eag.source.python.transformations.models import TextEdit


class RenameVisitor(ast.NodeVisitor):
    """Collects TextEdits to rename AST nodes based on exact semantic locations."""

    def __init__(
        self,
        document: SourceDocument,
        target_simple: str,
        new_name: str,
        content: str,
        locations: set[tuple[int, int]],
    ):
        self.doc = document
        self.target_simple = target_simple
        self.new_name = new_name.split(".")[-1] if "." in new_name else new_name
        self.source_lines = content.splitlines(keepends=True)
        self.edits: list[TextEdit] = []
        self.stats = {"symbols_renamed": 0, "references_updated": 0, "imports_updated": 0}
        self.locations = locations

    def _find_name_col(self, line: int, start_col: int, name: str) -> int:
        if 0 < line <= len(self.source_lines):
            line_text = self.source_lines[line - 1]
            idx = line_text.find(name, start_col)
            if idx != -1:
                return idx
            idx = line_text.find(name)
            if idx != -1:
                return idx
        return start_col

    def _add_edit(self, line: int, col: int, stat_key: str) -> None:
        if (line, col) in self.locations and not any(
            e.start_line == line and e.start_col == col for e in self.edits
        ):
            self.edits.append(
                TextEdit(
                    start_line=line,
                    start_col=col,
                    end_line=line,
                    end_col=col + len(self.target_simple),
                    new_text=self.new_name,
                )
            )
            self.stats[stat_key] += 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        col = self._find_name_col(node.lineno, node.col_offset, node.name)
        self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        col = self._find_name_col(node.lineno, node.col_offset, node.name)
        self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        col = self._find_name_col(node.lineno, getattr(node, "col_offset", 0), node.name)
        self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        col = self._find_name_col(node.lineno, node.col_offset, node.arg)
        self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._add_edit(node.lineno, node.col_offset, "references_updated")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        end_col = getattr(node, "end_col_offset", node.col_offset)
        start_col = end_col - len(node.attr)
        line = getattr(node, "end_lineno", node.lineno)
        self._add_edit(line, start_col, "references_updated")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == self.target_simple or alias.asname == self.target_simple:
                col = self._find_name_col(
                    getattr(alias, "lineno", node.lineno),
                    getattr(alias, "col_offset", node.col_offset),
                    self.target_simple,
                )
                if not any(
                    e.start_line == getattr(alias, "lineno", node.lineno) and e.start_col == col
                    for e in self.edits
                ):
                    self.edits.append(
                        TextEdit(
                            start_line=getattr(alias, "lineno", node.lineno),
                            start_col=col,
                            end_line=getattr(alias, "lineno", node.lineno),
                            end_col=col + len(self.target_simple),
                            new_text=self.new_name,
                        )
                    )
                    self.stats["imports_updated"] += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == self.target_simple or alias.asname == self.target_simple:
                col = self._find_name_col(
                    getattr(alias, "lineno", node.lineno),
                    getattr(alias, "col_offset", node.col_offset),
                    self.target_simple,
                )
                if not any(
                    e.start_line == getattr(alias, "lineno", node.lineno) and e.start_col == col
                    for e in self.edits
                ):
                    self.edits.append(
                        TextEdit(
                            start_line=getattr(alias, "lineno", node.lineno),
                            start_col=col,
                            end_line=getattr(alias, "lineno", node.lineno),
                            end_col=col + len(self.target_simple),
                            new_text=self.new_name,
                        )
                    )
                    self.stats["imports_updated"] += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            col = self._find_name_col(node.lineno, getattr(node, "col_offset", 0), node.name)
            self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            col = self._find_name_col(node.lineno, getattr(node, "col_offset", 0), node.name)
            self._add_edit(node.lineno, col, "symbols_renamed")
        self.generic_visit(node)
