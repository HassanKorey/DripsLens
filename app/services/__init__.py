"""Services module for DripsLens.

Provides resilient clients for Stellar Horizon, Soroban RPC, and GitHub REST API
with exponential backoff retries, rate-limit awareness, and fault tolerance.
"""

from app.services.github_fetcher import (
    GitHubClient,
    GitHubRateLimited,
    fetch_issues_for_repo,
    fetch_top_contributors,
)
from app.services.stellar_verifier import (
    StellarVerifier,
    check_stellar_account,
    verify_stellar_account,
)

__all__ = [
    "GitHubClient",
    "GitHubRateLimited",
    "StellarVerifier",
    "check_stellar_account",
    "fetch_issues_for_repo",
    "fetch_top_contributors",
    "verify_stellar_account",
]
