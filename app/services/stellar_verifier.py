"""Stellar Horizon and Soroban account verification service.

Implements exponential backoff retry logic (using tenacity) for Stellar Horizon
API calls, handling HTTP 429 (Rate Limit Exceeded) and 503 (Service Unavailable)
gracefully without crashing background scheduler workers.
"""

import logging
import os
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

STELLAR_HORIZON_URL = os.getenv("STELLAR_HORIZON_URL", "https://horizon-testnet.stellar.org")
SOROBAN_RPC_URL = os.getenv("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org:443")


class StellarHorizonRateLimitError(Exception):
    """Raised when Stellar Horizon responds with HTTP 429."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class StellarHorizonServiceUnavailableError(Exception):
    """Raised when Stellar Horizon responds with HTTP 503."""

    pass


class StellarVerifier:
    """Resilient verifier for Stellar Horizon accounts and contracts."""

    def __init__(
        self,
        horizon_url: str | None = None,
        max_retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        self.horizon_url = (horizon_url or STELLAR_HORIZON_URL).rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout

    async def _fetch_account_raw(self, account_id: str) -> httpx.Response:
        """Fetch account record from Horizon with exponential backoff for transient errors."""
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    StellarHorizonRateLimitError,
                    StellarHorizonServiceUnavailableError,
                )
            ),
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.horizon_url}/accounts/{account_id}")

                    if response.status_code == 429:
                        retry_after_str = response.headers.get("Retry-After")
                        retry_after = float(retry_after_str) if retry_after_str and retry_after_str.isdigit() else None
                        logger.warning(
                            "Stellar Horizon rate limited (429) for account %s, retry-after=%s",
                            account_id,
                            retry_after,
                        )
                        raise StellarHorizonRateLimitError("Horizon rate limit exceeded", retry_after=retry_after)

                    if response.status_code == 503:
                        logger.warning("Stellar Horizon service unavailable (503) for account %s", account_id)
                        raise StellarHorizonServiceUnavailableError("Horizon service temporarily unavailable")

                    return response

        raise RuntimeError("Unreachable retry state")

    async def verify_account(self, account_id: str | None) -> bool:
        """Verify whether a Stellar account exists on Horizon.

        Returns True if 200 OK.
        Returns False if 404 Not Found, invalid format, or rate-limited/unavailable after retries.
        Never raises exceptions that would terminate an APScheduler background job.
        """
        if not account_id or not isinstance(account_id, str):
            return False

        account_id = account_id.strip()
        if not account_id:
            return False

        try:
            response = await self._fetch_account_raw(account_id)
            return response.status_code == 200
        except (RetryError, StellarHorizonRateLimitError, StellarHorizonServiceUnavailableError) as e:
            logger.warning(
                "Stellar Horizon request failed after retries for %s: %s (defaulting to unverified)",
                account_id,
                e,
            )
            return False
        except httpx.HTTPError as e:
            logger.warning("HTTP error verifying Stellar account %s: %s", account_id, e)
            return False
        except Exception as e:
            logger.error("Unexpected error verifying Stellar account %s: %s", account_id, e)
            return False

    async def check_account_details(self, account_id: str) -> dict[str, Any]:
        """Perform a full verification check returning detailed status and metadata."""
        if not account_id or not isinstance(account_id, str):
            return {"status": "unverified", "detail": "Invalid or missing account ID"}

        account_id = account_id.strip()
        if len(account_id) != 56:
            return {"status": "unverified", "detail": "Account ID must be 56 characters"}

        try:
            response = await self._fetch_account_raw(account_id)
            if response.status_code == 200:
                data = response.json()
                balances = data.get("balances", [])
                native_balance = next(
                    (b.get("balance") for b in balances if b.get("asset_type") == "native"),
                    "0",
                )
                return {
                    "status": "verified",
                    "account_id": account_id,
                    "native_balance": native_balance,
                    "detail": f"Account active with {native_balance} XLM",
                }
            if response.status_code == 404:
                return {"status": "unverified", "account_id": account_id, "detail": "Account not found on Horizon"}

            return {
                "status": "unknown",
                "account_id": account_id,
                "detail": f"Unexpected Horizon status {response.status_code}",
            }
        except (RetryError, StellarHorizonRateLimitError) as e:
            logger.warning("Horizon rate limited after backoff for %s: %s", account_id, e)
            return {
                "status": "unknown",
                "account_id": account_id,
                "detail": "Rate limit exceeded on Horizon (429)",
            }
        except StellarHorizonServiceUnavailableError as e:
            logger.warning("Horizon 503 service unavailable for %s: %s", account_id, e)
            return {
                "status": "unknown",
                "account_id": account_id,
                "detail": "Horizon service temporarily unavailable (503)",
            }
        except Exception as e:
            logger.error("Failed to check account details for %s: %s", account_id, e)
            return {"status": "unknown", "account_id": account_id, "detail": str(e)}


# Global helper instance
_default_verifier = StellarVerifier()


async def verify_stellar_account(account_id: str) -> bool:
    """Convenience helper to verify a Stellar public key."""
    return await _default_verifier.verify_account(account_id)


async def check_stellar_account(account_id: str) -> dict[str, Any]:
    """Convenience helper for detailed account verification."""
    return await _default_verifier.check_account_details(account_id)
