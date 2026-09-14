"""Scrapes the Drips Wave approved repo list from drips.network.

The site is a SvelteKit app; approved repos (and point multipliers) are
server-rendered into the HTML. We therefore do two things:

1. Parse anchors / text with BeautifulSoup for github.com repo references.
2. Regex-scan the raw HTML (including embedded page data) for "owner/repo"
   patterns, deduplicating both sources.

Stellar account association: Drips pages do not currently expose per-repo
payout accounts, so the page only yields "weak" associations when a Stellar
address happens to appear near a repo mention. Strong association comes from
github_fetcher.discover_stellar_account() (stellar.toml / README context).

Pure parsing lives in `parse_repos_page` / `associate_stellar_accounts` so it
can be unit tested without network access.
"""

import itertools
import logging
import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

# github.com/owner/repo (optionally deeper path); captures "owner/repo"
GITHUB_REPO_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
)
# Stellar accounts/contracts: G.../C... + 55 base32 chars = 56 total.
# Kept as two patterns so callers can tell accounts from contracts apart.
STELLAR_ACCOUNT_RE = re.compile(r"\bG[A-Z2-7]{55}\b")
STELLAR_CONTRACT_RE = re.compile(r"\bC[A-Z2-7]{55}\b")
# A "weak" association needs the address and the repo mention close together.
STELLAR_ASSOCIATION_WINDOW = 400
# Bare "owner/repo" pairs appearing in embedded JSON / text; owner/repo must
# not be preceded by further path chars, and repo part must look like a name.
BARE_REPO_RE = re.compile(
    r"[\"'>\s:]([A-Za-z0-9_.-]{1,64})/([A-Za-z0-9_.-]{1,100})[\"'<\s,:\]}]",
)

_MULTIX = re.compile(r"(\d+(?:\.\d+)?)\s*[xX]\b")


@dataclass
class DripsRepo:
    full_name: str  # "owner/repo"
    owner: str
    name: str
    point_multiplier: float = 1.0
    html_url: str | None = None
    description: str | None = None
    # "strong" = verified in-repo source (stellar.toml / README context, set by
    # github_fetcher.discover_stellar_account); "weak" = address found near the
    # repo mention on the Drips page; None = no address linked.
    stellar_account: str | None = None
    stellar_account_source: str | None = None


@dataclass
class DripsReposPage:
    repos: list[DripsRepo] = field(default_factory=list)
    fetched_from: str | None = None
    fetched_at: str | None = None


def parse_repos_page(html: str) -> DripsReposPage:
    """Extract approved repos (and multipliers when available) from page HTML."""
    page = DripsReposPage()
    found: dict[str, DripsRepo] = {}

    soup = BeautifulSoup(html, "html.parser")

    # 1. Anchors pointing at github.com
    for a in soup.find_all("a", href=True):
        m = GITHUB_REPO_RE.match(a["href"].strip())
        if not m:
            continue
        owner, name = m.group(1), m.group(2)
        if owner in ("topics", "orgs", "search", "features", "collections", "trending"):
            continue  # github meta pages, not repos
        full_name = f"{owner}/{name}"
        if full_name not in found:
            found[full_name] = DripsRepo(
                full_name=full_name,
                owner=owner,
                name=name,
                html_url=f"https://github.com/{full_name}",
            )

    # 2. Raw scan of embedded JSON / text (Next.js flight data)
    for m in BARE_REPO_RE.finditer(html):
        owner, name = m.group(1), m.group(2)
        if name.endswith((".js", ".css", ".png", ".svg", ".map", ".ico", ".txt", ".json", ".webp")):
            continue
        if owner.lower() in ("github", "assets", "static", "vercel", "nextjs", "_next"):
            continue
        full_name = f"{owner}/{name}"
        if full_name not in found:
            found[full_name] = DripsRepo(
                full_name=full_name,
                owner=owner,
                name=name,
                html_url=f"https://github.com/{full_name}",
            )

    page.repos = list(found.values())
    associate_stellar_accounts(page, html)
    return page


def associate_stellar_accounts(page: DripsReposPage, html: str) -> None:
    """Best-effort: associate Stellar addresses on the page with repo mentions.

    Drips does not publish per-repo payout accounts today, so this only creates
    *weak* associations: an address whose nearest repo mention is within
    STELLAR_ASSOCIATION_WINDOW chars. Both the account and the mention must be
    unclaimed so a strong signal elsewhere is never downgraded.
    """
    if not page.repos:
        return
    positions: list[tuple[int, str]] = []
    for repo in page.repos:
        start = 0
        while (idx := html.find(repo.full_name, start)) != -1:
            positions.append((idx, repo.full_name))
            start = idx + 1
    positions.sort()

    for match in itertools.chain(STELLAR_ACCOUNT_RE.finditer(html), STELLAR_CONTRACT_RE.finditer(html)):
        pos, account = match.start(), match.group(0)
        nearest = min(
            (p for p in positions),
            key=lambda p: abs(p[0] - pos),
            default=None,
        )
        if nearest is None or abs(nearest[0] - pos) > STELLAR_ASSOCIATION_WINDOW:
            continue
        for repo in page.repos:
            if repo.full_name != nearest[1] or repo.stellar_account:
                continue
            repo.stellar_account = account
            repo.stellar_account_source = "weak:drips-page"
            break


def extract_multiplier_near(text: str, full_name: str) -> float | None:
    """Best-effort: find a '2x'/'4x' multiplier adjacent to a repo mention."""
    idx = text.find(full_name)
    if idx == -1:
        return None
    window = text[idx : idx + 300]
    m = _MULTIX.search(window)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def fetch_drips_repos(client: httpx.Client | None = None) -> DripsReposPage:
    """Fetch the live approved-repos page. Network call — keep out of unit tests."""
    url = settings.drips_repos_url
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": "DripsLens/0.1"})
    try:
        resp = client.get(url)
        resp.raise_for_status()
        page = parse_repos_page(resp.text)
        page.fetched_from = url
        return page
    finally:
        if own_client:
            client.close()
