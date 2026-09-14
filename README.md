# 💧 DripsLens

**DripsLens** aggregates, caches, and serves data about [Drips Wave](https://drips.network/wave/stellar/repos) (Stellar Program) approved repositories — open issues, contributor activity, point values, and on-chain verification — through a clean REST API and a minimal dashboard.

> Part of the Drips Wave Stellar Program ecosystem. Built as meta-tooling: it makes the Wave itself searchable and trackable.

## Features

| Feature | What it does |
|---|---|
| **Repo Explorer** | Browse 700+ approved repos, filter by language, multiplier (1x/2x/4x), issues, activity |
| **Issue Tracker** | All open Wave issues in one place, tiered by complexity (Trivial/Medium/High = 100/150/200 pts), claimed vs unclaimed |
| **Contributor Leaderboard** | Ranks contributors by merged PRs and points across Wave repos |
| **Repo Health Score** | 0–100 score per repo: open issues, CI status, last commit, README quality |
| **Stellar Verification** | Read-only Horizon API check of each repo's linked Stellar account/contract |
| **Data Refresh Engine** | APScheduler re-fetches everything every 6 hours — zero manual upkeep |

## Quick start (Docker)

```bash
cp .env.example .env        # optional: add GITHUB_TOKEN
docker compose up --build
```

- Dashboard: http://localhost:8000/
- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # SQLite works out of the box; Redis optional
alembic upgrade head        # or skip: tables auto-create on startup
uvicorn app.main:app --reload
```

Without Postgres/Redis the app falls back to SQLite and an in-process cache — handy for hacking.

## API overview

| Endpoint | Description |
|---|---|
| `GET /health` | App version + uptime |
| `GET /repos` | List/filter repos (`language`, `multiplier`, `min_health`, `q`, `verified`, `sort`, pagination) |
| `GET /repos/meta` | Aggregate stats for dashboards |
| `GET /repos/{id_or_owner/repo}` | Repo detail |
| `GET /repos/{id}/health` | Health score + component breakdown |
| `GET /issues` | Open issues (`complexity`, `claimed`, `repo`, `min_points`, pagination) |
| `GET /issues/stats` | Claimed/unclaimed counts, potential points |
| `GET /contributors/top` | Leaderboard ranked by points |

## Architecture

```
Layer 1  Data sources (consumed, not owned)
         drips.network ─ GitHub REST API ─ Stellar Horizon API
                        │
Layer 2  DripsLens backend (this repo)
         scrapers → PostgreSQL (snapshots) → Redis cache → FastAPI REST API
                        │
Layer 3  Minimal Jinja2 dashboard (improve it over time!)
```

See the code: `app/scrapers/` (fetchers), `app/models/` (DB schema), `app/routers/` (API), `app/scheduler/tasks.py` (refresh engine), `app/cache/` (Redis layer).

## Contributing

This repo is built *for contributors* — good first issues are the point. Start with [CONTRIBUTING.md](CONTRIBUTING.md), then browse the issue tracker: issues are labelled `trivial` (100 pts), `medium` (150 pts), `high` (200 pts).

## License

[MIT](LICENSE)
