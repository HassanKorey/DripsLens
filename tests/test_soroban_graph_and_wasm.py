from app.soroban.graph import build_invocation_graph
from app.soroban.wasm_analyzer import analyze_wasm


def test_build_invocation_graph():
    events = [
        {"contract_id": "C1", "topic": "call"},
        {"contract_id": "C2", "topic": "call"},
        {"contract_id": "C1", "topic": "transfer"},
    ]
    graph = build_invocation_graph(events)
    assert len(graph["nodes"]) == 2
    assert {"id": "C1"} in graph["nodes"]
    assert {"id": "C2"} in graph["nodes"]


def test_analyze_wasm_small():
    small_wasm = b"\x00asm" + b"\x00" * 100
    res = analyze_wasm(small_wasm)
    assert res["wasm_size_bytes"] == 104
    assert res["health_score"] == 100
    assert res["recommendations"] == []


def test_analyze_wasm_large():
    large_wasm = b"\x00asm" + b"\x00" * (70 * 1024)
    res = analyze_wasm(large_wasm)
    assert res["health_score"] == 50
    assert "Optimize WASM size" in res["recommendations"]
