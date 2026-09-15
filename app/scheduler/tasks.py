"""Data refresh engine — APScheduler background jobs.

Pipeline: Drips list -> enrich via GitHub -> verify Stellar accounts ->
compute health scores -> persist to Postgres. Runs at startup (optional) and
every REFRESH_INTERVAL_HOURS (default 6h) thereafter.
"""

import logging
import threading
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import redis_client as cache
from app.config import settings
from app.db.database import SessionLocal
from app.models import Contributor, Issue, Repo
from app.models.issue import COMPLEXITY_POINTS
from app.scrapers import drips_scraper, github_fetcher, stellar_verifier

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

COMPLEXITY_BY_LABEL = {"trivial": "trivial", "easy": "trivial", "good first issue": "trivial"}


def classify_complexity(labels: list[str]) -> str | None:
    """Map GitHub labels to Drips complexity tiers (trivial/medium/high)."""
    joined = " ".join(labels).lower()
    for needle, tier in (
        ("trivial", "trivial"),
        ("easy", "trivial"),
        ("good first issue", "trivial"),
        ("medium", "medium"),
        ("high", "high"),
        ("hard", "high"),
    ):
        if needle in joined:
            return tier
    return None


def compute_health_score(
    open_issues: int,
    has_ci: bool | None,
    last_commit_at: datetime | None,
    readme_score: float | None,
) -> float:
    """Repo Health Score (0..100): open issues available, CI, recency, README."""
    # Issue availability (0..40): reward having work available, cap at 20
    issue_component = min(open_issues, 20) / 20 * 40

    # CI (0..15)
    ci_component = 15.0 if has_ci else (7.5 if has_ci is None else 0.0)

    # Recency (0..25): full credit if committed within 30 days, decays to 0 at 365
    if last_commit_at is None:
        recency_component = 0.0
    else:
        age_days = max((datetime.now(UTC) - last_commit_at).days, 0)
        recency_component = max(0.0, 25.0 * (1 - age_days / 365))

    # README (0..20)
    readme_component = (readme_score or 0.0) * 20

    return round(issue_component + ci_component + recency_component + readme_component, 1)


def upsert_repo(db, item: drips_scraper.DripsRepo, signals: github_fetcher.RepoSignals | None) -> Repo:
    repo = db.query(Repo).filter(Repo.full_name == item.full_name).first()
    if repo is None:
        repo = Repo(full_name=item.full_name, owner=item.owner, name=item.name)
        db.add(repo)

    repo.owner = item.owner
    repo.name = item.name
    repo.description = item.description or (signals.description if signals else None)
    repo.html_url = item.html_url or f"https://github.com/{item.full_name}"
    repo.point_multiplier = item.point_multiplier
    if signals:
        repo.language = signals.language or repo.language
        repo.stars = signals.stars
        repo.forks = signals.forks
        repo.open_issues_count = signals.open_issues_count
        repo.has_ci = signals.has_ci
        repo.readme_score = signals.readme_score
        repo.last_push_at = signals.last_push_at
        if signals.last_commit_at:
            repo.last_commit_at = signals.last_commit_at
    repo.last_fetched_at = datetime.now(UTC)
    return repo


def sync_issues(db, repo: Repo, gh_issues: list[github_fetcher.GitHubIssue]) -> None:
    """Upsert GitHub issues for a repo, classifying complexity from labels."""
    for ghi in gh_issues:
        issue = db.query(Issue).filter(Issue.github_id == ghi.github_id).first()
        if issue is None:
            issue = Issue(github_id=ghi.github_id, repo_id=repo.id)
            db.add(issue)
        issue.repo_id = repo.id
        issue.number = ghi.number
        issue.title = ghi.title
        issue.state = ghi.state
        issue.html_url = ghi.html_url
        issue.labels = ghi.labels
        issue.assignees = ghi.assignees
        issue.body = ghi.body
        issue.complexity = classify_complexity(ghi.labels)
        issue.points = COMPLEXITY_POINTS.get(issue.complexity) if issue.complexity else None
        issue.claimed = bool(ghi.assignees)
        issue.created_at_gh = ghi.created_at
        issue.updated_at_gh = ghi.updated_at


def update_leaderboard(db, pr_activity: list[dict], repo_full_name: str, multiplier: float) -> None:
    """Fold merged PR activity into contributor aggregates."""
    now = datetime.now(UTC)
    by_login: dict[str, dict] = {}
    for pr in pr_activity:
        login = pr["login"]
        entry = by_login.setdefault(login, {"count": 0, "prs": []})
        entry["count"] += 1
        entry["prs"].append(
            {
                "repo": repo_full_name,
                "title": pr["title"],
                "number": pr["number"],
                "merged_at": pr["merged_at"],
                "url": pr["html_url"],
            }
        )

    for login, entry in by_login.items():
        c = db.query(Contributor).filter(Contributor.github_login == login).first()
        if c is None:
            c = Contributor(github_login=login, merged_prs=0, points=0)
            db.add(c)
        c.avatar_url = f"https://github.com/{login}.png"
        c.profile_url = f"https://github.com/{login}"
        c.merged_prs += entry["count"]
        # Points: 25 per merged PR, scaled by the repo's point multiplier
        c.points += int(entry["count"] * 25 * multiplier)
        repos = list(c.repos_contributed or [])
        if repo_full_name not in repos:
            repos.append(repo_full_name)
        c.repos_contributed = repos
        recent = list(c.recent_prs or []) + entry["prs"]
        c.recent_prs = sorted(recent, key=lambda p: p.get("merged_at") or "", reverse=True)[:25]
        c.last_fetched_at = now


def refresh_repos() -> dict:
    """Full pipeline refresh: Drips -> GitHub -> Stellar -> health -> DB."""
    logger.info("Refresh cycle starting")
    stats = {"repos": 0, "issues": 0, "contributors": 0, "verified": 0, "errors": 0}
    gh = github_fetcher.GitHubClient()

    try:
        page = drips_scraper.fetch_drips_repos()
    except Exception as exc:
        logger.error("Failed to fetch Drips repo list: %s", exc)
        return {**stats, "error": str(exc)}

    for item in page.repos:
        try:
            signals = gh.fetch_repo_signals(item.full_name)
        except github_fetcher.GitHubRateLimited:
            logger.warning("GitHub rate limited; aborting rest of refresh cycle")
            break
        except Exception as exc:
            logger.warning("GitHub fetch failed for %s: %s", item.full_name, exc)
            signals = None
            stats["errors"] += 1

        # Resolve the repo's linked Stellar account: the Drips page may carry a
        # (weak) association; otherwise look for strong in-repo sources such as
        # .well-known/stellar.toml or a wallet/payout mention in the README.
        # The account itself is then verified with a read-only Horizon check.
        account = item.stellar_account
        if not account:
            try:
                account, source = github_fetcher.discover_stellar_account(gh, item.full_name)
                if account:
                    logger.info("Discovered Stellar account for %s via %s", item.full_name, source)
            except github_fetcher.GitHubRateLimited:
                logger.warning("GitHub rate limited; aborting rest of refresh cycle")
                break
            except Exception as exc:
                logger.debug("Stellar account discovery failed for %s: %s", item.full_name, exc)

        try:
            issues = gh.fetch_open_issues(item.full_name)
        except Exception as exc:
            logger.warning("Issue fetch failed for %s: %s", item.full_name, exc)
            issues = []

        try:
            pr_activity = gh.fetch_merged_pr_activity(item.full_name)
        except Exception as exc:
            logger.warning("PR fetch failed for %s: %s", item.full_name, exc)
            pr_activity = []

        db = SessionLocal()
        try:
            repo = upsert_repo(db, item, signals)
            if account:
                repo.stellar_account = account
                result = stellar_verifier.verify_account(account)
                repo.stellar_verified = result.status == "verified"
                if result.status == "verified":
                    stats["verified"] += 1
            repo.health_score = compute_health_score(
                open_issues=repo.open_issues_count,
                has_ci=repo.has_ci,
                last_commit_at=repo.last_commit_at or repo.last_push_at,
                readme_score=repo.readme_score,
            )
            sync_issues(db, repo, issues)
            if pr_activity:
                update_leaderboard(db, pr_activity, item.full_name, item.point_multiplier)
            db.commit()
            stats["repos"] += 1
            stats["issues"] += len(issues)
        except Exception:
            db.rollback()
            logger.exception("DB update failed for %s", item.full_name)
            stats["errors"] += 1
        finally:
            db.close()

    # Invalidate cached API responses so fresh data is served (sync-safe: the
    # job runs in a worker thread, away from the event loop)
    cache.invalidate_prefix_sync("dripslens:")

    logger.info("Refresh cycle complete: %s", stats)
    return stats


def trigger_manual_refresh() -> str:
    """Kick off one immediate refresh cycle without waiting for the interval.

    Used to backfill repos whose data failed to save (e.g. DB errors) or to
    re-fetch on demand. When the APScheduler is running, schedules a deduped
    one-shot job (replace_existing keeps only one queued). Otherwise — e.g.
    SCHEDULER_ENABLED=false or no event loop — runs refresh_repos in a daemon
    background thread instead. Returns an identifier for what was started.
    """
    if scheduler.running:
        scheduler.add_job(
            refresh_repos,
            "date",
            run_date=datetime.now(UTC),
            id="refresh-manual",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("Manual refresh scheduled (job refresh-manual)")
        return "refresh-manual"

    threading.Thread(target=refresh_repos, name="manual-refresh", daemon=True).start()
    logger.info("Manual refresh started in background thread (scheduler not running)")
    return "refresh-thread"


def start_scheduler() -> AsyncIOScheduler:
    """Start APScheduler with the 6-hour refresh job (+ immediate run)."""
    if scheduler.get_job("refresh"):
        return scheduler
    if settings.initial_refresh_on_startup:
        scheduler.add_job(refresh_repos, "date", run_date=datetime.now(UTC), id="refresh-startup")
    scheduler.add_job(
        refresh_repos,
        "interval",
        hours=settings.refresh_interval_hours,
        id="refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: refresh every %sh (startup run: %s)",
        settings.refresh_interval_hours,
        settings.initial_refresh_on_startup,
    )
    return scheduler


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
