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


def test_build_invocation_graph_with_cross_contract_edges_and_deduplication():
    events = [
        {"contract_id": "C1", "target_contract_id": "C2", "topic": "call"},
        {"contract_id": "C1", "target_contract_id": "C2", "topic": "call"},
        {"contract_id": "C2", "data": {"to": "C3"}, "topic": "swap"},
        {"contract_id": "C1", "target_contract_id": "C1", "topic": "self_call"},
    ]
    graph = build_invocation_graph(events)
    assert graph["nodes"] == [{"id": "C1"}, {"id": "C2"}, {"id": "C3"}]
    assert graph["edges"] == [
        {"from": "C1", "to": "C2"},
        {"from": "C2", "to": "C3"},
    ]


def test_analyze_wasm_parses_export_section_and_debug_symbols():
    # Minimal WASM header + Export section (ID=7) with 3 exported functions
    # Export entry: [name_len=2, 'f','n', kind=0 (func), index=0]
    export_entries = (
        b"\x03"
        + b"\x02fn\x00\x00"
        + b"\x02go\x00\x01"
        + b"\x02ok\x00\x02"
    )
    export_section = bytes([7, len(export_entries)]) + export_entries
    wasm_with_exports = b"\x00asm\x01\x00\x00\x00" + export_section + b".debug_info"
    res = analyze_wasm(wasm_with_exports)
    assert res["exported_functions"] == 3
    assert res["health_score"] == 85
    assert "Strip debug symbols from production WASM binary" in res["recommendations"]
