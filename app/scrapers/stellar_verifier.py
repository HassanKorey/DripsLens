"""Backwards-compatibility shim for stellar_verifier service."""

from app.services.stellar_verifier import (
    STELLAR_HORIZON_URL,
    HorizonClient,
    StellarHorizonRateLimitError,
    StellarHorizonServiceUnavailableError,
    StellarVerifier,
    check_stellar_account,
    query_horizon_rpc,
    verify_stellar_account,
)

__all__ = [
    "STELLAR_HORIZON_URL",
    "HorizonClient",
    "StellarHorizonRateLimitError",
    "StellarHorizonServiceUnavailableError",
    "StellarVerifier",
    "check_stellar_account",
    "query_horizon_rpc",
    "verify_stellar_account",
]
