"""Stellar on-chain verification via the Horizon API (+ Soroban RPC for contracts).

Read-only. Returns a simple verified/unverified/unknown status per repo:
- G... accounts: Horizon GET /accounts/{id} -> 200 verified, 404 unverified
- C... contracts: Soroban RPC getLedgerEntries (requires STELLAR_RPC_URL)
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    account_or_contract: str | None
    status: str  # "verified" | "unverified" | "unknown"
    detail: str | None = None


def looks_like_account(value: str) -> bool:
    return value.startswith("G") and len(value) == 56


def looks_like_contract(value: str) -> bool:
    return value.startswith("C") and len(value) == 56


def _check_horizon(account_id: str) -> VerificationResult:
    url = f"{settings.stellar_horizon_url.rstrip('/')}/accounts/{account_id}"
    try:
        resp = httpx.get(url, timeout=15.0, headers={"User-Agent": "DripsLens/0.1"})
    except httpx.HTTPError as exc:
        logger.warning("Horizon request failed for %s: %s", account_id, exc)
        return VerificationResult(account_id, "unknown", detail=str(exc))

    if resp.status_code == 200:
        data = resp.json()
        balances = data.get("balances", [])
        xlm = next((b for b in balances if b.get("asset_type") == "native"), None)
        detail = "account exists on Horizon" + (
            f"; XLM balance {xlm.get('balance')}" if xlm else ""
        )
        return VerificationResult(account_id, "verified", detail=detail)
    if resp.status_code == 404:
        return VerificationResult(account_id, "unverified", detail="no such account on Horizon")
    return VerificationResult(account_id, "unknown", detail=f"Horizon returned {resp.status_code}")


def _check_contract(contract_id: str) -> VerificationResult:
    """Verify a Soroban contract exists via getLedgerEntries (needs RPC URL)."""
    rpc_url = settings.stellar_rpc_url
    if not rpc_url:
        return VerificationResult(
            contract_id, "unknown", detail="STELLAR_RPC_URL not configured; cannot verify contracts"
        )
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getLedgerEntries",
        "params": {"keys": [{"contractData": {"contract": contract_id, "key": "ledgerKeyContractInstance"}}]},
    }
    try:
        resp = httpx.post(rpc_url, json=payload, timeout=15.0)
        resp.raise_for_status()
        entries = resp.json().get("result", {}).get("entries", [])
        if entries:
            return VerificationResult(contract_id, "verified", detail="contract instance found on ledger")
        return VerificationResult(contract_id, "unverified", detail="no contract instance on ledger")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Soroban RPC request failed for %s: %s", contract_id, exc)
        return VerificationResult(contract_id, "unknown", detail=str(exc))


def verify_account(account_or_contract: str | None) -> VerificationResult:
    """Verify a G... account or C... contract. None/invalid -> unknown."""
    if not account_or_contract:
        return VerificationResult(None, "unknown", detail="no Stellar account linked")
    if looks_like_account(account_or_contract):
        return _check_horizon(account_or_contract)
    if looks_like_contract(account_or_contract):
        return _check_contract(account_or_contract)
    return VerificationResult(account_or_contract, "unknown", detail="not a valid G.../C... address")
