# Contributing to DripsLens

Thanks for helping make the Drips Wave ecosystem trackable! This project is designed for contributors — most code areas map directly to a labelled issue.

## Try it live

- 🌐 **Live Demo**: https://dripslens.onrender.com
- 📖 **API Docs**: https://dripslens.onrender.com/docs
- ❤️ **Health Check**: https://dripslens.onrender.com/health

The production instance auto-deploys on every push to `main` — what's merged is what's live. Use it to explore the API without setting up a local stack.

## Workflow

1. **Pick an issue** — comment to claim it so maintainers can assign you.
2. **Fork & branch** — `git checkout -b feat/<issue-number>-short-description`
3. **Implement** — match the issue spec; keep PRs focused on one issue.
4. **Test** — add/adjust tests for your change:
   ```bash
   pytest
   ```
5. **Lint** — CI runs `ruff check app tests`; run it locally too:
   ```bash
   ruff check app tests
   ```
6. **Open a PR** — reference the issue (`Closes #N`), describe what you implemented and any tradeoffs.

A maintainer reviews against the issue spec, CI must pass, then it's merged.

## Project layout

```
app/
  routers/       API endpoints (repos, issues, contributors, health)
  scrapers/      drips.network scraper, GitHub fetcher, Stellar verifier
  models/        SQLAlchemy models
  db/            engine/session + Alembic migrations
  cache/         Redis (with in-process fallback)
  scheduler/     APScheduler refresh jobs
  templates/     Jinja2 dashboard
tests/           pytest suite (no network needed)
```

## Conventions

- Python 3.11+, type hints encouraged
- Format/lint with **ruff** (config in `pyproject.toml`)
- Endpoints return plain JSON dicts; timestamps are ISO-8601 UTC
- Scrapers: keep *pure parsing* functions separate from network calls so they're unit-testable
- No secrets in code — use env vars (see `.env.example`)

## Local stack

Full stack via Docker (`docker compose up`) or run with SQLite/no Redis for quick iteration — the app degrades gracefully.

## Questions?

Open a discussion or ask in the issue — maintainers aim to respond within 24–48 hours.
