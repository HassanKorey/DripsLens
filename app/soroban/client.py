import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SOROBAN_RPC_URL = os.getenv("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org:443")


class SorobanRPCException(Exception):
    """Base exception for Soroban RPC errors."""
    pass


class SorobanRateLimited(SorobanRPCException):
    """Raised when Soroban RPC node responds with HTTP 429 rate limit."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SorobanServiceUnavailable(SorobanRPCException):
    """Raised when Soroban RPC node responds with HTTP 503 unavailable."""
    pass


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((httpx.HTTPError, SorobanRateLimited, SorobanServiceUnavailable)),
    reraise=True,
)
async def rpc_request(method: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=15.0) as client:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        response = await client.post(SOROBAN_RPC_URL, json=payload)

        if response.status_code == 429:
            retry_after_str = response.headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str and retry_after_str.isdigit() else 2.0
            logger.warning("Soroban RPC rate limited (429), retry_after=%.1f", retry_after)
            raise SorobanRateLimited("Soroban RPC 429 Rate Limit Exceeded", retry_after=retry_after)

        if response.status_code == 503:
            logger.warning("Soroban RPC service unavailable (503)")
            raise SorobanServiceUnavailable("Soroban RPC 503 Service Unavailable")

        response.raise_for_status()
        data = response.json()
        if "error" in data:
            error_obj = data["error"]
            if isinstance(error_obj, dict) and error_obj.get("code") == 429:
                raise SorobanRateLimited(f"Soroban RPC rate limit error: {error_obj}")
            raise SorobanRPCException(f"RPC Error: {error_obj}")
        return data.get("result")


async def get_health() -> Any:
    return await rpc_request("getHealth")


async def get_events(start_ledger: int) -> Any:
    return await rpc_request("getEvents", {"startLedger": start_ledger})


async def get_ledger_entries(keys: list[str]) -> Any:
    return await rpc_request("getLedgerEntries", {"keys": keys})
