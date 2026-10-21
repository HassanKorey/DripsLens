"""Backwards-compatibility shim for stellar_verifier service."""

from app.services.stellar_verifier import (
    STELLAR_HORIZON_URL,
    StellarHorizonRateLimitError,
    StellarHorizonServiceUnavailableError,
    StellarVerifier,
    check_stellar_account,
    verify_stellar_account,
)

__all__ = [
    "STELLAR_HORIZON_URL",
    "StellarHorizonRateLimitError",
    "StellarHorizonServiceUnavailableError",
    "StellarVerifier",
    "check_stellar_account",
    "verify_stellar_account",
]
