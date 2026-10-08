from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/soroban", tags=["Analytics"])


@router.get("/graph")
async def get_graph() -> dict[str, list[dict[str, Any]]]:
    return {"nodes": [{"id": "C1"}], "edges": []}
