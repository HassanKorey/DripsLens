"""Backwards-compatibility shim for github_fetcher service."""

from app.services.github_fetcher import (
    GITHUB_API_BASE,
    GITHUB_TOKEN,
    GitHubClient,
    GitHubRateLimited,
    GitHubRetryableRateLimit,
    GitHubServiceUnavailableError,
    fetch_issues_for_repo,
    fetch_top_contributors,
)

__all__ = [
    "GITHUB_API_BASE",
    "GITHUB_TOKEN",
    "GitHubClient",
    "GitHubRateLimited",
    "GitHubRetryableRateLimit",
    "GitHubServiceUnavailableError",
    "fetch_issues_for_repo",
    "fetch_top_contributors",
]
