from eag.graph.algorithms.models import MetricsReport
from eag.graph.models import EngineeringGraph


class MetricsAnalyzer:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph

    def run(self) -> MetricsReport:
        in_degrees = {n.id: 0 for n in self._graph.nodes}
        out_degrees = {n.id: 0 for n in self._graph.nodes}
        node_map = {n.id: n for n in self._graph.nodes}

        for edge in self._graph.edges:
            out_degrees[edge.source] = out_degrees.get(edge.source, 0) + 1
            in_degrees[edge.target] = in_degrees.get(edge.target, 0) + 1

        # Change your max() calls to explicitly use a lambda expression:
        # Safely compute metrics matching your internal variable structures
        most_ref_id = max(in_degrees, key=lambda k: in_degrees[k]) if in_degrees else None

        # Note: If your metrics implementation uses a combined dictionary name
        # other than total_degrees, ensure it matches that collection name.
        most_conn_id = max(in_degrees, key=lambda k: in_degrees[k]) if in_degrees else None

        return MetricsReport(
            nodes=len(self._graph.nodes),
            edges=len(self._graph.edges),
            most_referenced=node_map.get(most_ref_id) if most_ref_id else None,
            most_connected=node_map.get(most_conn_id) if most_conn_id else None,
        )
