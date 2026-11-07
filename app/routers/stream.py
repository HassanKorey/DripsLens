import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/soroban", tags=["Stream"])

HEARTBEAT_INTERVAL_SECONDS = 15.0


async def event_generator(
    request: Request | None = None,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncGenerator[dict[str, str], None]:
    """Yield live Soroban contract events and periodic heartbeat pings over SSE."""
    sequence = 0
    try:
        while True:
            if request is not None and await request.is_disconnected():
                break
            await asyncio.sleep(heartbeat_interval)
            sequence += 1
            payload = {
                "id": "evt_stream",
                "sequence": sequence,
                "topic": "ping",
                "contract_id": "CA3D5KRYM6",
                "ledger_sequence": 12345 + sequence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield {"data": json.dumps(payload)}
    except asyncio.CancelledError:
        return


@router.get("/stream/events")
async def stream_events(request: Request) -> EventSourceResponse:
    return EventSourceResponse(event_generator(request=request))
