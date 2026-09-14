"""GitHub REST API client: issues, labels, contributor/PR activity, repo signals.

Handles:
- Token auth (raises rate limit from 60 to 5,000 req/h when GITHUB_TOKEN set)
- Rate-limit awareness (X-RateLimit-Remaining / Retry-After)
- Retries with exponential backoff on 5xx / network errors
"""

import base64
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GitHubRateLimited(Exception):
    pass


@dataclass
class GitHubIssue:
    github_id: int
    number: int
    title: str
    state: str
    html_url: str | None
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    body: str | None = None
    is_pull_request: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class RepoSignals:
    full_name: str
    stars: int = 0
    forks: int = 0
    open_issues_count: int = 0
    has_ci: bool | None = None
    readme_score: float | None = None
    last_commit_at: datetime | None = None
    last_push_at: datetime | None = None
    language: str | None = None
    description: str | None = None


def _parse_gh_time(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str | None = None, max_retries: int | None = None):
        self.token = token if token is not None else settings.github_token
        self.base_url = (base_url or settings.github_api_base).rstrip("/")
        self.max_retries = settings.github_max_retries if max_retries is None else max_retries

    # -- low-level request with retry + rate-limit handling -------------------

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DripsLens/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_json(self, url: str, params: dict | None = None) -> dict | list:
        """GET a JSON resource with retries, backoff and rate-limit awareness."""
        attempt = 0
        last_error: Exception | None = None
        while attempt <= self.max_retries:
            attempt += 1
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(url, headers=self._headers(), params=params or {})
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(min(2**attempt, 30))
                continue

            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                wait = max(reset - int(time.time()), 1)
                logger.warning("GitHub rate limit hit; reset in ~%ss", wait)
                raise GitHubRateLimited(f"rate limited; reset in {wait}s")

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                time.sleep(retry_after)
                last_error = RuntimeError("429 from GitHub")
                continue

            if resp.status_code >= 500:
                last_error = RuntimeError(f"{resp.status_code} from GitHub")
                time.sleep(min(2**attempt, 30))
                continue

            if resp.status_code == 404:
                raise LookupError(f"not found: {url}")

            resp.raise_for_status()
            return resp.json()

        raise last_error or RuntimeError("GitHub request failed")

    # -- high-level fetchers ---------------------------------------------------

    def fetch_open_issues(self, full_name: str, max_pages: int = 5) -> list[GitHubIssue]:
        """Fetch open issues (PRs excluded — GitHub returns PRs as issues too)."""
        issues: list[GitHubIssue] = []
        for page in range(1, max_pages + 1):
            data = self.get_json(
                f"{self.base_url}/repos/{full_name}/issues",
                params={"state": "open", "per_page": 100, "page": page},
            )
            for item in data:
                if "pull_request" in item:
                    continue  # PR, not an issue
                issues.append(
                    GitHubIssue(
                        github_id=item["id"],
                        number=item["number"],
                        title=item.get("title") or "",
                        state=item.get("state", "open"),
                        html_url=item.get("html_url"),
                        labels=[lbl["name"] for lbl in item.get("labels", [])],
                        assignees=[a["login"] for a in item.get("assignees", []) or []],
                        body=(item.get("body") or "")[:4000] or None,
                        is_pull_request=False,
                        created_at=_parse_gh_time(item.get("created_at")),
                        updated_at=_parse_gh_time(item.get("updated_at")),
                    )
                )
            if len(data) < 100:
                break
        return issues

    def fetch_repo(self, full_name: str) -> dict:
        return self.get_json(f"{self.base_url}/repos/{full_name}")

    def fetch_repo_signals(self, full_name: str) -> RepoSignals:
        """Stars/forks/language, last push, CI presence and README quality."""
        data = self.fetch_repo(full_name)
        signals = RepoSignals(
            full_name=full_name,
            stars=int(data.get("stargazers_count", 0)),
            forks=int(data.get("forks_count", 0)),
            open_issues_count=int(data.get("open_issues_count", 0)),
            last_push_at=_parse_gh_time(data.get("pushed_at")),
            language=data.get("language"),
            description=data.get("description"),
        )

        # CI detection: look for workflows in .github/workflows
        try:
            tree = self.get_json(f"{self.base_url}/repos/{full_name}/git/trees/HEAD", params={"recursive": 0})
            paths = [t.get("path", "") for t in tree.get("tree", [])]
            signals.has_ci = any(p.startswith(".github/workflows/") for p in paths)
        except Exception:
            signals.has_ci = None

        # README quality: length + headings + code blocks -> 0..1 score
        try:
            readme = self.get_json(f"{self.base_url}/repos/{full_name}/readme")
            import base64

            text = base64.b64decode(readme.get("content", "")).decode("utf-8", errors="replace")
            signals.readme_score = score_readme(text)
        except Exception:
            signals.readme_score = None

        return signals

    def fetch_merged_pr_activity(self, full_name: str, max_pages: int = 3) -> list[dict]:
        """Merged PRs (author, title, merged_at) for leaderboard scoring."""
        prs: list[dict] = []
        for page in range(1, max_pages + 1):
            data = self.get_json(
                f"{self.base_url}/repos/{full_name}/pulls",
                params={"state": "closed", "per_page": 100, "page": page, "sort": "updated", "direction": "desc"},
            )
            for pr in data:
                if pr.get("merged_at"):
                    prs.append(
                        {
                            "login": (pr.get("user") or {}).get("login", "unknown"),
                            "title": pr.get("title") or "",
                            "number": pr.get("number"),
                            "merged_at": pr.get("merged_at"),
                            "html_url": pr.get("html_url"),
                        }
                    )
            if len(data) < 100:
                break
        return prs


# Stellar accounts/contracts discovered from in-repo files (strong sources):
# .well-known/stellar.toml `ACCOUNTS` entries, or wallet/payout mentions in
# README context. G.../C... + 55 base32 chars = 56 total.
STELLAR_TOML_PATHS = (".well-known/stellar.toml", "stellar.toml")
WALLET_KEYWORD_RE = re.compile(
    r"(payout|wallet|funding|donation|donate|payment address)", re.I
)
STELLAR_ACCOUNT_RE = re.compile(r"\bG[A-Z2-7]{55}\b")
STELLAR_CONTRACT_RE = re.compile(r"\bC[A-Z2-7]{55}\b")
# Address must appear within this many chars of a wallet keyword in a README.
WALLET_CONTEXT_WINDOW = 120


def _extract_toml_account(text: str) -> str | None:
    """First G.../C... address in a stellar.toml ACCOUNTS declaration.

    Handles both documented formats: the top-level inline array
    (`ACCOUNTS = ["G..."]`, including multi-line arrays) and `[[ACCOUNTS]]`
    sections. Comments and other sections/keys are ignored.
    """
    in_accounts = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[["):
            in_accounts = "ACCOUNTS" in stripped.upper()
            continue
        if stripped.startswith("["):
            in_accounts = False  # unrelated section, e.g. [DOCUMENTATION]
            continue
        if not in_accounts:
            # inline top-level array format: ACCOUNTS = ["G...", ...]
            if "=" in stripped and stripped.upper().startswith("ACCOUNTS"):
                in_accounts = True
            else:
                continue
        # Inside [[ACCOUNTS]] (keys like ADDRESS = "G...") or the inline array.
        m = STELLAR_ACCOUNT_RE.search(line) or STELLAR_CONTRACT_RE.search(line)
        if m:
            return m.group(0)
    return None


def _extract_readme_account(text: str) -> str | None:
    """G.../C... address near a wallet/payout keyword in a README."""
    for pattern in (STELLAR_ACCOUNT_RE, STELLAR_CONTRACT_RE):
        for m in pattern.finditer(text):
            ctx = text[max(0, m.start() - WALLET_CONTEXT_WINDOW) : m.start()]
            if WALLET_KEYWORD_RE.search(ctx):
                return m.group(0)
    return None


def discover_stellar_account(
    client: "GitHubClient", full_name: str
) -> tuple[str | None, str | None]:
    """Find the repo's linked Stellar account/contract from in-repo sources.

    Strong association: stellar.toml [[ACCOUNTS]] wins over wallet-context
    README mentions. Returns (account_or_contract, source) or (None, None).
    """
    for path in STELLAR_TOML_PATHS:
        try:
            data = client.get_json(f"{client.base_url}/repos/{full_name}/contents/{path}")
        except LookupError:
            continue
        except GitHubRateLimited:
            raise
        except Exception as exc:
            logger.debug("stellar.toml fetch failed for %s: %s", full_name, exc)
            continue

        try:
            text = base64.b64decode(data.get("content", "")).decode("utf-8", "ignore")
        except Exception:
            continue
        account = _extract_toml_account(text)
        if account:
            return account, "strong:stellar.toml"

    try:
        readme = client.get_json(f"{client.base_url}/repos/{full_name}/readme")
    except GitHubRateLimited:
        raise
    except Exception as exc:
        logger.debug("readme fetch failed for %s: %s", full_name, exc)
        return None, None
    try:
        text = base64.b64decode(readme.get("content", "")).decode("utf-8", "ignore")
    except Exception:
        return None, None
    account = _extract_readme_account(text)
    if account:
        return account, "strong:readme"
    return None, None


def score_readme(text: str) -> float:
    """README quality heuristic in 0..1: length, structure, code samples."""
    if not text:
        return 0.0
    length_score = min(len(text) / 3000, 1.0)
    headings = len(re.findall(r"^#{1,3} ", text, flags=re.M))
    code_blocks = text.count("```") // 2
    structure = min((headings + code_blocks) / 10, 1.0)
    has_install = 1.0 if ("install" in text.lower() or "usage" in text.lower()) else 0.0
    return round(min(0.5 * length_score + 0.3 * structure + 0.2 * has_install, 1.0), 3)
