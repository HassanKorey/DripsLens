"""Tests for scraper parsing + pure logic (no network access)."""

import base64
from datetime import UTC, datetime, timedelta

from app.scheduler.tasks import (
    classify_complexity,
    compute_health_score,
    refresh_repos,
    update_leaderboard,
)
from app.scrapers.drips_scraper import parse_repos_page
from app.scrapers.github_fetcher import (
    _extract_readme_account,
    _extract_toml_account,
    discover_stellar_account,
    score_readme,
)
from app.scrapers.stellar_verifier import looks_like_account, looks_like_contract, verify_account

# --- drips_scraper.parse_repos_page -----------------------------------------


def test_parse_repos_page_finds_github_links():
    html = """
    <div><a href="https://github.com/stellar/soroban-examples">link</a>
    <a href="https://github.com/acme/cool-python-app">x</a></div>
    """
    page = parse_repos_page(html)
    names = {r.full_name for r in page.repos}
    assert {"stellar/soroban-examples", "acme/cool-python-app"} <= names


def test_parse_repos_page_ignores_github_meta_pages():
    html = '<a href="https://github.com/topics/rust">topics</a><a href="https://github.com/orgs/stellar">orgs</a>'
    page = parse_repos_page(html)
    assert page.repos == []


def test_parse_repos_page_deduplicates():
    html = '<a href="https://github.com/a/b">x</a><a href="https://github.com/a/b">y</a>'
    page = parse_repos_page(html)
    assert len(page.repos) == 1


# --- github_fetcher.score_readme --------------------------------------------


def test_score_readme_empty():
    assert score_readme("") == 0.0


def test_score_readme_good_document():
    text = "# Title\n" + "x" * 3000 + "\n## Install\n```bash\npip install x\n```\n"
    assert score_readme(text) >= 0.75


# --- stellar_verifier --------------------------------------------------------


def test_account_shape_detection():
    g = "G" + "A" * 55
    c = "C" + "A" * 55
    assert looks_like_account(g)
    assert not looks_like_account(c)
    assert looks_like_contract(c)
    assert not looks_like_contract(g)


def test_verify_account_none_is_unknown():
    assert verify_account(None).status == "unknown"


def test_verify_account_invalid_is_unknown():
    assert verify_account("not-an-address").status == "unknown"


# --- scheduler.tasks pure helpers -------------------------------------------


def test_classify_complexity():
    assert classify_complexity(["trivial", "docs"]) == "trivial"
    assert classify_complexity(["medium"]) == "medium"
    assert classify_complexity(["HIGH", "bug"]) == "high"
    assert classify_complexity([]) is None


def test_health_score_perfect_repo():
    now = datetime.now(UTC)
    score = compute_health_score(open_issues=25, has_ci=True, last_commit_at=now, readme_score=1.0)
    assert score == 100.0


def test_health_score_stale_repo():
    old = datetime.now(UTC) - timedelta(days=400)
    score = compute_health_score(open_issues=0, has_ci=False, last_commit_at=old, readme_score=0.0)
    assert score < 10


# --- stellar account discovery ----------------------------------------------


def _acct(ch: str = "A") -> str:
    return "G" + ch * 55


def test_drips_repo_stellar_fields_default_none():
    page = parse_repos_page('<a href="https://github.com/a/b">x</a>')
    assert page.repos[0].stellar_account is None
    assert page.repos[0].stellar_account_source is None


def test_parse_repos_page_associates_account_near_repo():
    acct = _acct()
    html = (
        '<a href="https://github.com/a/b">a / b</a>'
        f' <span>Payout account: {acct}</span>'
    )
    page = parse_repos_page(html)
    assert page.repos[0].stellar_account == acct
    assert page.repos[0].stellar_account_source == "weak:drips-page"


def test_parse_repos_page_ignores_distant_address():
    acct = _acct()
    html = (
        '<a href="https://github.com/a/b">x</a>'
        + "<p>filler</p>" * 100
        + f'<span>{acct}</span>'
    )
    page = parse_repos_page(html)
    assert page.repos[0].stellar_account is None


def test_extract_toml_account_inline_array():
    acct = _acct()
    assert _extract_toml_account(f'ACCOUNTS = ["{acct}"]') == acct


def test_extract_toml_account_multiline_array():
    acct = _acct()
    toml = f"ACCOUNTS = [\n  \"{acct}\",\n]\n"
    assert _extract_toml_account(toml) == acct


def test_extract_toml_account_section_format():
    acct = _acct()
    toml = f"[[ACCOUNTS]]\nADDRESS = \"{acct}\"\n"
    assert _extract_toml_account(toml) == acct


def test_extract_toml_account_ignores_other_sections():
    acct = _acct()
    toml = f"[DOCUMENTATION]\nnote = \"{acct}\"\n"
    assert _extract_toml_account(toml) is None


def test_extract_readme_account_with_wallet_context():
    acct = _acct()
    assert _extract_readme_account(f"## Funding\nPayout account: {acct}") == acct


def test_extract_readme_account_without_context():
    acct = _acct()
    assert _extract_readme_account(f"The genesis hash was {acct} in old docs") is None


def test_discover_stellar_account_prefers_toml():
    toml_acct = _acct("A")

    class FakeClient:
        base_url = "https://api.github.com"

        def get_json(self, url, params=None):
            if url.endswith("/contents/.well-known/stellar.toml"):
                return {"content": base64.b64encode(f'ACCOUNTS = ["{toml_acct}"]'.encode()).decode()}
            raise LookupError(url)

    account, source = discover_stellar_account(FakeClient(), "a/b")
    assert account == toml_acct
    assert source == "strong:stellar.toml"


def test_discover_stellar_account_falls_back_to_readme():
    readme_acct = _acct("C")

    class FakeClient:
        base_url = "https://api.github.com"

        def get_json(self, url, params=None):
            if url.endswith("/readme"):
                return {"content": base64.b64encode(f"Wallet: {readme_acct}".encode()).decode()}
            raise LookupError(url)

    account, source = discover_stellar_account(FakeClient(), "a/b")
    assert account == readme_acct
    assert source == "strong:readme"


def test_refresh_repos_verifies_discovered_account(monkeypatch, db_session):
    """Scraper -> discovery -> verifier -> DB pipeline (no network)."""
    from app.models import Repo
    from app.scrapers import drips_scraper, github_fetcher, stellar_verifier

    acct = _acct("D")
    page = drips_scraper.DripsReposPage(
        repos=[drips_scraper.DripsRepo(full_name="acme/pipeline-repo", owner="acme", name="pipeline-repo")]
    )
    verify_calls: list[str] = []

    def fake_verify(account_or_contract):
        verify_calls.append(account_or_contract)
        return stellar_verifier.VerificationResult(account_or_contract, "verified", detail="test")

    class FakeClient:
        base_url = "https://api.github.com"

        def get_json(self, url, params=None):
            if "/contents/.well-known/stellar.toml" in url:
                raise LookupError(url)
            if url.endswith("/readme"):
                return {"content": base64.b64encode(f"Payout wallet: {acct}".encode()).decode()}
            if url.endswith("/repos/acme/pipeline-repo"):
                return {
                    "stargazers_count": 5,
                    "forks_count": 1,
                    "open_issues_count": 3,
                    "pushed_at": "2026-09-01T00:00:00Z",
                    "language": "Rust",
                    "description": "pipeline test repo",
                }
            if url.endswith("/git/trees/HEAD"):
                return {"tree": []}
            return []  # issues / pulls lists

        def fetch_repo_signals(self, full_name):
            return github_fetcher.RepoSignals(
                full_name=full_name,
                stars=5,
                forks=1,
                open_issues_count=3,
                has_ci=False,
                readme_score=0.5,
                last_push_at=datetime.now(UTC),
                language="Rust",
                description="pipeline test repo",
            )

        def fetch_open_issues(self, full_name, max_pages=5):
            return []

        def fetch_merged_pr_activity(self, full_name, max_pages=3):
            return []

    monkeypatch.setattr(drips_scraper, "fetch_drips_repos", lambda: page)
    monkeypatch.setattr(github_fetcher, "GitHubClient", FakeClient)
    monkeypatch.setattr(stellar_verifier, "verify_account", fake_verify)

    stats = refresh_repos()

    assert stats["repos"] == 1
    assert stats["verified"] == 1
    assert verify_calls == [acct]  # exactly one verification call

    repo = db_session.query(Repo).filter(Repo.full_name == "acme/pipeline-repo").one()
    assert repo.stellar_account == acct
    assert repo.stellar_verified is True


def test_update_leaderboard_aggregates(db_session):
    from app.models import Contributor

    prs = [
        {"login": "alice", "title": "Fix", "number": 1, "merged_at": "2026-09-01T00:00:00Z", "html_url": "u1"},
        {"login": "alice", "title": "Improve", "number": 2, "merged_at": "2026-09-02T00:00:00Z", "html_url": "u2"},
    ]
    update_leaderboard(db_session, prs, "acme/x", multiplier=2.0)
    db_session.commit()

    alice = db_session.query(Contributor).filter(Contributor.github_login == "alice").one()
    assert alice.merged_prs == 2
    assert alice.points == 100  # 2 PRs * 25 * 2.0
    assert "acme/x" in alice.repos_contributed
