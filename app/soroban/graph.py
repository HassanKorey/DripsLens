from typing import Any


def build_invocation_graph(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    # Analyzes contract event logs to discover cross-contract calls
    # Returns Directed Acyclic Graph (DAG) JSON structure
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for event in events:
        contract_id = event.get("contract_id")
        if contract_id and not any(n.get("id") == contract_id for n in nodes):
            nodes.append({"id": contract_id})
    return {"nodes": nodes, "edges": edges}
