# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/) and commits use the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format.

## [Unreleased]

## [0.1.0] — 2026-09-14

### Added
- FastAPI backend: `/health`, `/repos`, `/issues`, `/contributors/top` REST endpoints with filtering and pagination
- Scrapers: drips.network approved-repo parser, GitHub fetcher (issues/PRs/repo signals) with retry + rate-limit handling, Stellar Horizon verifier
- PostgreSQL models for repos, issues, contributors; Alembic initial migration
- Redis cache layer with 5-minute TTL and in-process fallback
- Repo Health Score (issues, CI, recency, README) with `/repos/{id}/health` breakdown
- APScheduler refresh engine (6h cycle) with startup run
- Jinja2 dashboard: repo list, issue table, repo detail page
- robots.txt and sitemap.xml
- pytest suite (endpoints + pure scraper logic) and GitHub Actions CI (ruff + pytest)
- Docker Compose stack: Postgres + Redis + app
- Community health files: README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, MAINTAINERS, LICENSE

[Unreleased]: https://github.com/your-org/drips-lens/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/drips-lens/releases/tag/v0.1.0
