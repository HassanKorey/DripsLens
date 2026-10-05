import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import os

SOROBAN_RPC_URL = os.getenv("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org:443")

class SorobanRPCException(Exception):
    pass

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def rpc_request(method: str, params: dict = None):
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        response = await client.post(SOROBAN_RPC_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise SorobanRPCException(f"RPC Error: {data['error']}")
        return data.get("result")

async def get_health():
    return await rpc_request("getHealth")

async def get_events(start_ledger: int):
    return await rpc_request("getEvents", {"startLedger": start_ledger})

async def get_ledger_entries(keys: list):
    return await rpc_request("getLedgerEntries", {"keys": keys})
