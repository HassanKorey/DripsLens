import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/soroban", tags=["Stream"])


async def event_generator(request: Request | None = None) -> AsyncGenerator[dict[str, str], None]:
    while True:
        if request and await request.is_disconnected():
            break
        await asyncio.sleep(5)
        yield {"data": '{"id": "evt_stream", "topic": "ping"}'}


@router.get("/stream/events")
async def stream_events(request: Request) -> EventSourceResponse:
    return EventSourceResponse(event_generator(request))
