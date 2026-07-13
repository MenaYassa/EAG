import json
from dataclasses import asdict
from typing import Any

from eag.graph.models import EngineeringGraph


class GraphExporter:
    def to_json(self, graph: EngineeringGraph) -> str:
        """Converts an EngineeringGraph instance to a serialized JSON string."""
        # Force an explicit cast to dict[str, Any] to avoid union inference blocks
        data: dict[str, Any] = asdict(graph)

        # Type-safe normalization for node attributes
        if "nodes" in data and isinstance(data["nodes"], (list, tuple)):
            for node in data["nodes"]:
                if isinstance(node, dict) and "kind" in node:
                    node["kind"] = (
                        node["kind"].value if hasattr(node["kind"], "value") else node["kind"]
                    )

        # Type-safe normalization for edge relationships
        if "edges" in data and isinstance(data["edges"], (list, tuple)):
            for edge in data["edges"]:
                if isinstance(edge, dict) and "relationship" in edge:
                    edge["relationship"] = (
                        edge["relationship"].value
                        if hasattr(edge["relationship"], "value")
                        else edge["relationship"]
                    )

        # Type-safe normalization for statistics dictionary mapping
        if "statistics" in data and isinstance(data["statistics"], dict):
            stats = data["statistics"]
            if "relationship_counts" in stats and isinstance(stats["relationship_counts"], dict):
                counts: dict[str, int] = {}
                for rel, count in stats["relationship_counts"].items():
                    rel_key = rel.value if hasattr(rel, "value") else str(rel)
                    counts[rel_key] = count
                stats["relationship_counts"] = counts

        return json.dumps(data, indent=2)
