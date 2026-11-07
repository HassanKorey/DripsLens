from typing import Any


def build_invocation_graph(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Analyze contract event logs to discover cross-contract calls and return a DAG JSON topology."""
    nodes: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()

    def _add_node(cid: str | None) -> None:
        if cid and isinstance(cid, str) and cid not in seen_nodes:
            seen_nodes.add(cid)
            nodes.append({"id": cid})

    for event in events:
        if not isinstance(event, dict):
            continue
        source = event.get("contract_id") or event.get("from") or event.get("caller")
        _add_node(source)

        data = event.get("data")
        target = (
            event.get("target_contract_id")
            or event.get("to")
            or event.get("callee")
            or (
                data.get("target_contract_id") or data.get("to") or data.get("callee")
                if isinstance(data, dict)
                else None
            )
        )
        _add_node(target)

        if source and target and source != target:
            pair = (source, target)
            if pair not in seen_edges:
                seen_edges.add(pair)
                edges.append({"from": source, "to": target})

    return {"nodes": nodes, "edges": edges}
