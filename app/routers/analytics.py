from fastapi import APIRouter

router = APIRouter(prefix="/soroban", tags=["Analytics"])

@router.get("/graph")
async def get_graph():
    return {"nodes": [{"id": "C1"}], "edges": []}
