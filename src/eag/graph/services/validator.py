from dataclasses import dataclass, field

from eag.graph.models import EngineeringGraph


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphValidationReport:
    healthy: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class GraphValidator:
    def validate(self, graph: EngineeringGraph) -> GraphValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        node_ids = {n.id for n in graph.nodes}

        # Check for duplicate nodes
        if len(node_ids) != len(graph.nodes):
            errors.append("Duplicate nodes detected.")

        # Check for dangling edges
        for edge in graph.edges:
            if edge.source not in node_ids:
                errors.append(f"Dangling edge source: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Dangling edge target: {edge.target}")

        # Check statistics
        if graph.statistics.nodes != len(graph.nodes):
            errors.append("Node count mismatch in statistics.")
        if graph.statistics.edges != len(graph.edges):
            errors.append("Edge count mismatch in statistics.")

        return GraphValidationReport(healthy=len(errors) == 0, errors=errors, warnings=warnings)
