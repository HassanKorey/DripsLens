# Contributing to DripsLens

Thank you for your interest in contributing to **DripsLens**! DripsLens is an open-source analytics engine and search platform that makes the Drips Wave ecosystem trackable, searchable, and verifiable.

We welcome contributions ranging from bug fixes and documentation improvements to new analytics scrapers, test suites, and Soroban indexing capabilities.

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Development Workflow

### 1. Prerequisites

- Python 3.10+ (Python 3.12 recommended)
- Git
- Virtual environment (`venv` or `poetry`)

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/HassanKorey/DripsLens.git
cd DripsLens

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Branch Naming Conventions

Use atomic, descriptive branches:
- `feat/short-description`: New features or API capabilities
- `fix/short-description`: Bug fixes or error resilience
- `test/short-description`: Test suite expansions or regression fixtures
- `docs/short-description`: Documentation and OpenAPI schema annotations
- `refactor/short-description`: Code restructuring without behavioral change

### 4. Conventional Commit Messages

We adhere to [Conventional Commits](https://www.conventionalcommits.org/):
```text
feat(services): implement exponential backoff retry for Stellar Horizon
fix(scheduler): prevent background worker crash on HTTP 429
test(api): add async integration coverage for /health and /repos
docs(governance): define multi-maintainer review workflows
```

---

## Quality Standards & CI Gates

Every pull request must pass the automated GitHub Actions CI pipeline:

1. **Linting & Code Formatting**:
   ```bash
   ruff check .
   ```
2. **Static Type Checking**:
   ```bash
   mypy app
   ```
3. **Async Test Suite & Coverage (90%+ Required)**:
   ```bash
   pytest tests/ -v --cov=app --cov-fail-under=90
   ```
4. **No Network Dependency in Tests**:
   Unit and integration tests must never issue live network requests. Always mock external HTTP calls (GitHub REST, Stellar Horizon, Soroban RPC) using `unittest.mock.patch` or `httpx.MockTransport`.

---

## Drips Wave Complexity Tiers

When picking or scoping issues under the Drips Wave program, tasks are categorized by complexity points:

- **Trivial (100 pts)**:
  - Single-function additions or bug fixes.
  - Unit tests for specific modules.
  - Adding metadata fields or timestamp telemetry (e.g., `/health` uptime).
- **Medium (150 pts)**:
  - Implementing retry and rate-limiting resilience (`tenacity` backoff).
  - Multi-parameter query filters and pagination handling.
  - Schema enhancements and caching layer optimizations.
- **High (200 pts)**:
  - Full end-to-end integration test suites across multiple subsystems.
  - WASM bytecode analyzers and cross-contract DAG graph engines.
  - Real-time event streaming architectures (SSE) and background worker fault tolerance.

---

## Multi-Maintainer Review Process

1. Submit your PR against the `main` branch.
2. An assigned domain maintainer will review within **48 hours** (see [MAINTAINERS.md](MAINTAINERS.md)).
3. Address feedback and keep commit history atomic.
4. Once approvals are met and CI is green, a maintainer will merge your PR.
