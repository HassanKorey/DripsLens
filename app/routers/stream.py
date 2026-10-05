from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio

router = APIRouter(prefix="/soroban", tags=["Stream"])

async def event_generator():
    while True:
        await asyncio.sleep(5)
        yield {"data": '{"id": "evt_stream", "topic": "ping"}'}

@router.get("/stream/events")
async def stream_events():
    return EventSourceResponse(event_generator())
