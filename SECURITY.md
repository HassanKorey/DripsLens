# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| main branch | ✅ |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

- Use GitHub's [private vulnerability reporting](../../security/advisories/new) on this repository, or
- Contact the maintainers listed in [MAINTAINERS.md](MAINTAINERS.md).

Include: description, reproduction steps, affected endpoints/components, and any logs. You'll get an acknowledgement within 72 hours.

## Scope notes

DripsLens is a read-only aggregator:

- It holds **no user credentials, wallets, or keys**. The optional `GITHUB_TOKEN` only raises API rate limits.
- All third-party integrations (GitHub, Drips, Stellar Horizon) are read-only HTTP fetches.
- Highest-risk areas: scraper input handling (HTML/JSON parsing of external sites) and the GitHub fetcher. SSRF/prototype-pollution style reports against those areas are welcome.
- The dashboard renders user-adjacent data (issue titles, repo descriptions) — XSS reports there are in scope.
- The production instance runs at https://dripslens.onrender.com (auto-deploys from `main`) — when reporting, reference the affected endpoint on the live instance where possible.

We aim to triage and ship fixes for confirmed issues within 14 days.
