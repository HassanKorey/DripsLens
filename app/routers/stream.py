import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/soroban", tags=["Stream"])


async def event_generator() -> AsyncGenerator[dict[str, str], None]:
    while True:
        await asyncio.sleep(5)
        yield {"data": '{"id": "evt_stream", "topic": "ping"}'}


@router.get("/stream/events")
async def stream_events() -> EventSourceResponse:
    return EventSourceResponse(event_generator())
