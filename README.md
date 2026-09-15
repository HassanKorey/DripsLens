# 💧 DripsLens

[![CI](https://github.com/HassanKorey/DripsLens/actions/workflows/ci.yml/badge.svg)](https://github.com/HassanKorey/DripsLens/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
cp .env.example .env        # GITHUB_TOKEN is required — see the note below
docker compose up --build
```

> **`GITHUB_TOKEN` is required — this is not optional for real operation.** Unauthenticated GitHub API calls are capped at 60 requests/hour. The 6-hour refresh cycle makes 3–5 calls per repo, and Stellar account discovery adds 2 more calls per repo — so without a token the refresh hits rate limits and fails almost immediately. Generate a token (no scopes needed to read public repos) and put it in `.env` before starting the app.

- Dashboard: `/`
- API docs (Swagger): `/docs`
- Health: `/health`

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # GITHUB_TOKEN is required — see note in Quick start; SQLite works out of the box, Redis optional
alembic upgrade head        # or skip: tables auto-create on startup
uvicorn app.main:app --reload
```

Without Postgres/Redis the app falls back to SQLite and an in-process cache — handy for hacking.

## Deployment

This project is deployable on [Railway](https://railway.app). A `railway.toml` is included (Dockerfile builder, `/health` healthcheck), with a `Procfile` as a fallback start command.

Required environment variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string, e.g. `postgresql+psycopg2://user:pass@host:5432/dripslens` |
| `REDIS_URL` | Redis connection string, e.g. `redis://host:6379/0` (omit for in-process cache) |
| `GITHUB_TOKEN` | GitHub token (required — see the rate-limit note in Quick start) |

Set these in the Railway service settings; they are injected as env vars at runtime and are read via pydantic-settings from `app/config.py`.

Optional variables:

| Variable | Purpose |
|---|---|
| `ADMIN_TOKEN` | When set, `/admin/refresh*` requires an `X-Admin-Token: <value>` header. Leave unset only if your deployment is private. |

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
| `POST /admin/refresh` | Trigger a full data refresh on demand (send `X-Admin-Token` header when `ADMIN_TOKEN` is set) |
| `GET /admin/refresh/status` | Refresh job status — next scheduled run, manual job pending |

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
