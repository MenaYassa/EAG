from typing import Any

from eag.graph.algorithms.models import ImpactReport, PathReport
from eag.graph.models import EngineeringGraph, GraphNode
from eag.graph.services.dependency_classifier import DependencyCategory, DependencyClassifier


class GraphFormatter:
    def __init__(self, classifier: DependencyClassifier | None = None) -> None:
        self._classifier = classifier or DependencyClassifier()

    def format_dependencies(self, node: GraphNode, dependencies: list[GraphNode]) -> str:
        grouped = self._classifier.group(dependencies)
        lines = [f"Dependencies for {node.name}", "─" * 40]

        for cat in [
            DependencyCategory.INTERNAL,
            DependencyCategory.STDLIB,
            DependencyCategory.THIRD_PARTY,
        ]:
            items = sorted(grouped.get(cat, []), key=lambda n: n.name)
            if items:
                lines.append(f"\n{cat.value.capitalize()}")
                lines.append("────────────────────")
                for item in items:
                    lines.append(f"  • {item.name}")

        return "\n".join(lines)

    def format_why(self, node: GraphNode, incoming: list[Any], outgoing: list[Any]) -> str:

        lines = [f"{node.name}", "─" * 40, "Referenced because:"]

        # UPGRADED: Changed from Mapping to dict to natively support .setdefault() mutation
        rel_map: dict[str, list[tuple[str, str, str]]] = {}

        for edge in incoming:
            src_node = edge[0]
            rel = edge[1].value.upper()
            rel_map.setdefault(rel, []).append((src_node.name, "->", node.name))

        for edge in outgoing:
            tgt_node = edge[0]
            rel = edge[1].value.upper()
            rel_map.setdefault(rel, []).append((node.name, "->", tgt_node.name))

        for rel, items in sorted(rel_map.items()):
            lines.append(f"\n{rel}")
            lines.append("────────────────────")
            for src, _, tgt in sorted(items):
                lines.append(f"  • {src} -> {tgt}")

        lines.append(f"\nTotal relationships: {len(incoming) + len(outgoing)}")
        return "\n".join(lines)

    def format_impact(self, report: ImpactReport) -> str:
        lines = [
            "Engineering Impact",
            "────────────────────────",
            f"Changed Node:  {report.changed_node.name}",
            "",
            "Direct Impact:",
        ]
        if not report.direct:
            lines.append("  None")
        else:
            for d in sorted(report.direct, key=lambda n: n.name):
                lines.append(f"  • {d.name}")

        lines.extend(["", "Indirect Impact:"])
        if not report.indirect:
            lines.append("  None")
        else:
            for d in sorted(report.indirect, key=lambda n: n.name):
                lines.append(f"  • {d.name}")

        lines.extend(["", f"Maximum Depth: {report.depth}", f"Affected Nodes: {report.total}"])
        return "\n".join(lines)

    def format_path(self, report: PathReport) -> str:
        lines = [f"Path: {report.start.name} -> {report.end.name}", "─" * 40]
        if report.distance == -1:
            lines.append("  No path found.")
        else:
            for i, node in enumerate(report.path):
                if i > 0:
                    lines.append("  │")
                    lines.append("  ▼")
                lines.append(f"  {node.name} ({node.kind.value})")
            lines.append("")
            lines.append(f"Distance: {report.distance}")
        return "\n".join(lines)

    def format_graph_stats(self, graph: EngineeringGraph) -> str:
        lines = [
            "Engineering Graph",
            "─" * 40,
            f"Nodes:      {graph.statistics.nodes}",
            f"Edges:      {graph.statistics.edges}",
            "",
            "Relationships:",
        ]
        for rel, count in sorted(
            graph.statistics.relationship_counts.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"  {rel.value:<15} {count}")
        return "\n".join(lines)
