# DripsLens Governance & Maintainers

This document outlines the governance model, maintainer roster, and review workflows for the DripsLens project.

## Maintainer Roster

| Name | GitHub Handle | Role | Focus Areas | Contact |
|---|---|---|---|---|
| **Hassan Akorede (EDUN)** | [@HassanKorey](https://github.com/HassanKorey) | Project Lead / Core Maintainer | Architecture, Soroban RPC, System Deployments, CI/CD | `edunhassan1006@gmail.com` |
| **Hirthik Balaji C** | [@HirthikBalaji](https://github.com/HirthikBalaji) | Co-Maintainer | Core API, Uptime Monitoring, Integration Suites | `hirthikbalaji2006@gmail.com` |
| **Lang** | [@1412346915-lang](https://github.com/1412346915-lang) | Co-Maintainer | Stellar Horizon Verifiers, Network Fallbacks, Scrapers | `1412346915@qq.com` |

---

## Review Workflows & PR Assignment Rules

To sustain code quality, prevent single-maintainer bottlenecks, and foster active multi-contributor collaboration:

### 1. Automatic PR Assignment by Domain

Pull requests are routed based on modified paths:

- **Services & Resiliency (`app/services/**`, `app/scrapers/**`)**:
  - Primary Reviewer: [@1412346915-lang](https://github.com/1412346915-lang)
  - Secondary Reviewer: [@HassanKorey](https://github.com/HassanKorey)
  - Criteria: Verify retry backoff logic (tenacity), 429/503 rate-limit resilience, and zero outbound network calls in test fixtures.

- **API Routes & Endpoint Contracts (`app/routers/**`, `tests/test_api_*.py`, `tests/test_health.py`)**:
  - Primary Reviewer: [@HirthikBalaji](https://github.com/HirthikBalaji)
  - Secondary Reviewer: [@HassanKorey](https://github.com/HassanKorey)
  - Criteria: Verify OpenAPI response schemas, backwards compatibility, and monotonic uptime counters.

- **Core Architecture, Database Models, Schedulers & CI (`app/main.py`, `app/db/**`, `app/models/**`, `app/scheduler/**`, `.github/**`)**:
  - Mandatory Reviewer: [@HassanKorey](https://github.com/HassanKorey)
  - Secondary Reviewer: Any co-maintainer
  - Criteria: Requires schema migration validation, async connection pool safety, and APScheduler non-blocking task isolation.

### 2. Approval Policy

- **Standard PRs (Features, Bugfixes, Tests, Docs)**:
  - Requires **at least 1 approving review** from an assigned domain maintainer.
  - Requires green CI checks: Ruff (linting), Mypy (type safety), and Pytest with 90%+ code coverage.
- **Architectural & Schema Modifications**:
  - Requires **at least 2 maintainer approvals**, including [@HassanKorey](https://github.com/HassanKorey).

### 3. Review Response SLA

Maintainers commit to an initial triage review within **48 hours** for all community contributions and peer pull requests. If a reviewer is unavailable, reviews escalate automatically to the Project Lead.

---

## Maintainer Meetings & Consensus

Decisions regarding roadmap pivots, breaking API versions, or dependency updates are made by consensus among maintainers during async review rounds on GitHub issues and PR discussions. If consensus cannot be reached, final arbitration rests with the Project Lead.
