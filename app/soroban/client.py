import os
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

SOROBAN_RPC_URL = os.getenv("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org:443")
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("SOROBAN_RPC_TIMEOUT", "10.0"))
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class SorobanRPCException(Exception):
    """Structured exception raised when Soroban JSON-RPC calls fail or exhaust retries."""


def _raise_on_exhausted_retries(retry_state: RetryCallState) -> Any:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempts = retry_state.attempt_number
    raise SorobanRPCException(
        f"Soroban RPC request failed after {attempts} attempts: {exc}"
    ) from exc


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    retry_error_callback=_raise_on_exhausted_retries,
)
async def rpc_request(method: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        response = await client.post(SOROBAN_RPC_URL, json=payload)
        if response.status_code in TRANSIENT_STATUS_CODES:
            response.raise_for_status()
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise SorobanRPCException(f"RPC Error: {data['error']}")
        return data.get("result")


async def get_health() -> Any:
    return await rpc_request("getHealth")


async def get_events(start_ledger: int) -> Any:
    return await rpc_request("getEvents", {"startLedger": start_ledger})


async def get_ledger_entries(keys: list[str]) -> Any:
    return await rpc_request("getLedgerEntries", {"keys": keys})
