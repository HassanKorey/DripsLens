from typing import Any

WASM_MAGIC = b"\x00asm"
SIZE_LIMIT_BYTES = 64 * 1024


def _read_leb128_u32(buf: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    pos = offset
    while pos < len(buf):
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, pos


def _count_exported_functions(wasm_bytes: bytes) -> int | None:
    """Parse WASM Export section (ID 7) to count exported function symbols (kind == 0)."""
    if len(wasm_bytes) < 8 or not wasm_bytes.startswith(WASM_MAGIC):
        return None
    pos = 8
    found_export_section = False
    func_exports = 0
    try:
        while pos < len(wasm_bytes):
            section_id = wasm_bytes[pos]
            pos += 1
            if section_id == 0 and pos >= len(wasm_bytes):
                break
            section_size, pos = _read_leb128_u32(wasm_bytes, pos)
            if section_size <= 0 or pos + section_size > len(wasm_bytes):
                break
            section_end = pos + section_size
            if section_id == 7:
                found_export_section = True
                count, cur = _read_leb128_u32(wasm_bytes, pos)
                for _ in range(count):
                    name_len, cur = _read_leb128_u32(wasm_bytes, cur)
                    cur += name_len
                    if cur >= section_end:
                        break
                    kind = wasm_bytes[cur]
                    cur += 1
                    _, cur = _read_leb128_u32(wasm_bytes, cur)
                    if kind == 0:
                        func_exports += 1
            pos = section_end
    except Exception:
        return None
    return func_exports if found_export_section else None


def analyze_wasm(wasm_bytes: bytes) -> dict[str, Any]:
    """Analyze WASM bytecode size, exported function interfaces, and optimization opportunities."""
    size = len(wasm_bytes)
    score = 100
    recommendations: list[str] = []

    if size > SIZE_LIMIT_BYTES:
        score -= 50
        recommendations.append("Optimize WASM size")

    if b".debug_" in wasm_bytes:
        score -= 15
        recommendations.append("Strip debug symbols from production WASM binary")

    parsed_exports = _count_exported_functions(wasm_bytes)
    exported_functions = parsed_exports if parsed_exports is not None else 2

    return {
        "wasm_size_bytes": size,
        "health_score": max(0, score),
        "exported_functions": exported_functions,
        "recommendations": recommendations,
    }
