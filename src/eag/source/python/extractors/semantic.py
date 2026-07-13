import ast

from eag.source.models import SemanticRelationship
from eag.source.state import SemanticKind


class SemanticVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str) -> None:
        self.module = module_name
        self.rels: list[SemanticRelationship] = []
        self.class_stack: list[str] = []
        self.func_stack: list[str] = []
        self.base_exclusions = [
            "ABC",
            "Protocol",
            "Enum",
            "Generic",
            "Exception",
            "Error",
            "StrEnum",
            "IntEnum",
            "Flag",
            "IntFlag",
        ]

    @property
    def current_class(self) -> str | None:
        return self.class_stack[-1] if self.class_stack else None

    @property
    def current_context(self) -> str:
        parts = [self.module] + self.class_stack + self.func_stack
        return ".".join(parts)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)

        # Inheritance
        for base in node.bases:
            base_name = ast.unparse(base)
            if base_name and base_name[0].isupper() and base_name not in self.base_exclusions:
                self.rels.append(
                    SemanticRelationship(
                        source=f"{self.module}.{node.name}",
                        target=base_name,
                        kind=SemanticKind.INHERITS,
                    )
                )

        self.generic_visit(node)
        self.class_stack.pop()

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # Architecture Linker: Constructor injection
        # e.g., def __init__(self, builder: GraphBuilder)
        if self.current_class and isinstance(node.target, ast.Name) and node.annotation:
            ann = ast.unparse(node.annotation)
            if ann.startswith("'") or ann.startswith('"'):
                ann = ann[1:-1]
            if ann and ann[0].isupper():
                self.rels.append(
                    SemanticRelationship(
                        source=f"{self.module}.{self.current_class}",
                        target=ann,
                        kind=SemanticKind.USES,
                    )
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.func_stack.append(node.name)

        # Architecture Linker: Constructor injection
        # e.g., def __init__(self, builder: GraphBuilder)
        if node.name == "__init__" and self.current_class:
            class_qname = f"{self.module}.{self.current_class}"
            for arg in node.args.args:
                if arg.arg != "self" and arg.annotation:
                    ann = ast.unparse(arg.annotation)
                    if ann.startswith("'") or ann.startswith('"'):
                        ann = ann[1:-1]
                    if ann and ann[0].isupper():
                        self.rels.append(
                            SemanticRelationship(
                                source=class_qname,
                                target=ann,
                                kind=SemanticKind.USES,
                            )
                        )

        self.generic_visit(node)
        self.func_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handles async functions cleanly with identical semantic USES checking."""
        self.func_stack.append(node.name)

        # Architecture Linker: Constructor injection
        # e.g., def __init__(self, builder: GraphBuilder)
        if node.name == "__init__" and self.current_class:
            class_qname = f"{self.module}.{self.current_class}"
            for arg in node.args.args:
                if arg.arg != "self" and arg.annotation:
                    ann = ast.unparse(arg.annotation)
                    if ann.startswith("'") or ann.startswith('"'):
                        ann = ann[1:-1]
                    if ann and ann[0].isupper():
                        self.rels.append(
                            SemanticRelationship(
                                source=class_qname,
                                target=ann,
                                kind=SemanticKind.USES,
                            )
                        )

        self.generic_visit(node)
        self.func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        caller = self.current_context
        if not caller:
            return

        call_target_str = ast.unparse(node.func)

        # Event Relationships
        if "publish" in call_target_str.lower() and node.args:
            event_expr = node.args[0]
            if isinstance(event_expr, ast.Call):
                event_name = ast.unparse(event_expr.func)
                if event_name and event_name[0].isupper():
                    self.rels.append(
                        SemanticRelationship(
                            source=caller,
                            target=event_name,
                            kind=SemanticKind.PUBLISHES_EVENT,
                        )
                    )
            elif isinstance(event_expr, ast.Name):
                event_name = event_expr.id
                if event_name and event_name[0].isupper():
                    self.rels.append(
                        SemanticRelationship(
                            source=caller,
                            target=event_name,
                            kind=SemanticKind.PUBLISHES_EVENT,
                        )
                    )
        elif "subscribe" in call_target_str.lower() and node.args:
            event_name_expr = node.args[0]
            event_name = ast.unparse(event_name_expr)
            if event_name and event_name[0].isupper():
                self.rels.append(
                    SemanticRelationship(
                        source=caller,
                        target=event_name,
                        kind=SemanticKind.SUBSCRIBES_EVENT,
                    )
                )


class SemanticExtractor:
    def extract(self, tree: ast.AST, module_name: str) -> tuple[SemanticRelationship, ...]:
        """Preserves original parameter mapping order to keep call sites green."""
        visitor = SemanticVisitor(module_name)
        visitor.visit(tree)
        return tuple(visitor.rels)
