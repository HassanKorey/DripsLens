import asyncio
from app.soroban.client import get_events

async def ingest_soroban_events():
    print("Ingesting soroban events...")
    # Polling Soroban RPC for new contract events
    try:
        events = await get_events(0)
        # Store to DB logic would go here
    except Exception as e:
        print(f"Error ingesting events: {e}")
