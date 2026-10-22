# DripsLens — Drips Wave Issue Backlog & Contributor Guide

This directory documents the scoped backlog of open-source engineering tasks for **DripsLens** under the Drips Wave program. Every issue strictly adheres to the *Drips Wave Maintainer Guide ("Creating Meaningful Issues")*:

- **No low-value or artificial issues**: Zero typo fixes or cosmetic rewordings. Every task represents concrete SDK tooling, fault tolerance, test coverage, or analytics features.
- **Explicit Acceptance Criteria**: Every issue provides deterministic criteria that can be validated via unit tests and automated CI checks.
- **Target Modules**: Explicit code pointers directing contributors to specific files and interfaces.
- **Strict Complexity Tiers**: Categorized strictly into **Trivial (100 pts)**, **Medium (150 pts)**, or **High (200 pts)**.

---

## Issue Backlog Overview

| Issue ID | Title | Complexity | Points | Target Modules |
|---|---|---|---|---|
| **#11** | Add OpenAPI / FastAPI Metadata Tags, Response Models, and Route Docstrings | Trivial | 100 pts | `app/schemas/soroban.py`, `app/routers/soroban.py` |
| **#12** | Implement Robust Exponential Backoff & Retry Logic for Soroban RPC Client | Trivial | 100 pts | `app/soroban/client.py`, `tests/test_soroban_client.py` |
| **#13** | Build Async Soroban Contract Event Ingestion Worker Using getEvents RPC | Medium | 150 pts | `app/soroban/indexer.py`, `app/scheduler/tasks.py` |
| **#14** | Develop Storage Footprint & TTL Expiry Monitoring Endpoint for Soroban Contracts | Medium | 150 pts | `app/routers/soroban.py`, `app/soroban/client.py` |
| **#15** | Build Pytest Async Test Suite for Soroban Client and Scraper Modules | Medium | 150 pts | `tests/test_soroban_scrapers.py`, `pyproject.toml` |
| **#16** | Create Responsive Tailwind CSS Web Explorer for Soroban Contracts and Invocations | Medium | 150 pts | `app/templates/soroban_explorer.html`, `app/static/js/explorer.js` |
| **#17** | Implement Server-Sent Events (SSE) Live Feed for Soroban Contract Events | High | 200 pts | `app/routers/stream.py`, `app/main.py` |
| **#18** | Build Soroban Contract WASM Bytecode Analyzer and Health Scoring Engine | High | 200 pts | `app/soroban/wasm_analyzer.py`, `app/routers/soroban.py` |
| **#19** | Develop Cross-Contract Invocation Graph Analyzer | High | 200 pts | `app/soroban/graph.py`, `app/routers/analytics.py` |
| **#20** | Implement Automated GitHub Actions CI for Ruff Linting, Mypy Type Checking, and Pytest | High | 200 pts | `.github/workflows/ci.yml`, `pyproject.toml` |

---

## Detailed Issue Specifications

### Issue #11: Add OpenAPI / FastAPI Metadata Tags, Response Models, and Route Docstrings
- **Complexity Tier**: Trivial (100 Points)
- **Problem & Context**: Interactive API documentation at `/docs` lacks structured response models, schema descriptions, and realistic payload examples for Soroban analytics endpoints, making SDK generation and integration difficult.
- **Target Files**:
  - `app/schemas/soroban.py`
  - `app/routers/soroban.py`
  - `tests/test_soroban_endpoints.py`
- **Acceptance Criteria**:
  - [ ] Define descriptive Pydantic schemas in `app/schemas/soroban.py` (`ContractMetricsSchema`, `ContractTTLSchema`, `ContractHealthSchema`) with `Field(description=...)` metadata.
  - [ ] Add `response_model` annotations to all endpoints in `app/routers/soroban.py`.
  - [ ] Ensure Swagger UI at `/docs` renders realistic `200 OK` response examples for `/soroban/events` and `/soroban/contracts/{contract_id}/metrics`.
  - [ ] Add explicit operation docstrings detailing path parameters, return types, and potential error states.
  - [ ] All existing tests pass and Ruff checks remain clean.

---

### Issue #12: Implement Robust Exponential Backoff & Retry Logic for Soroban RPC Client
- **Complexity Tier**: Trivial (100 Points)
- **Problem & Context**: Public Soroban RPC nodes occasionally experience rate-limiting (HTTP 429) or transient 503 errors during periods of high ledger activity. Unhandled exceptions terminate background indexers.
- **Target Files**:
  - `app/soroban/client.py`
  - `tests/test_soroban_client.py`
  - `tests/test_services_resilience.py`
- **Acceptance Criteria**:
  - [ ] Implement exponential backoff retry logic (using `tenacity`) for RPC requests with configurable min/max intervals and attempt caps.
  - [ ] Catch HTTP 429 and parse `Retry-After` header when provided by the RPC proxy.
  - [ ] Transient failures retry up to 3 times before raising a structured `SorobanRPCException`.
  - [ ] Unit tests verify retry behavior under simulated 429 and 503 responses without live network calls.

---

### Issue #13: Build Async Soroban Contract Event Ingestion Worker Using getEvents RPC
- **Complexity Tier**: Medium (150 Points)
- **Problem & Context**: To maintain an up-to-date index of smart contract activity across the Drips Wave ecosystem, DripsLens requires an asynchronous background worker that regularly queries Soroban RPC `getEvents`.
- **Target Files**:
  - `app/soroban/indexer.py`
  - `app/scheduler/tasks.py`
  - `app/models/soroban.py`
- **Acceptance Criteria**:
  - [ ] Async worker polls `getEvents` starting from the highest indexed ledger sequence.
  - [ ] Parsed event envelopes are persisted to the database without duplicate ledger entries.
  - [ ] Worker is scheduled via APScheduler at 15-minute intervals inside `resilient_job_wrapper`.
  - [ ] Handles RPC downtime gracefully by logging warnings and preserving state for the next run.

---

### Issue #14: Develop Storage Footprint & TTL Expiry Monitoring Endpoint for Soroban Contracts
- **Complexity Tier**: Medium (150 Points)
- **Problem & Context**: Soroban smart contracts require storage rent; instances that exceed their Time-To-Live (TTL) sequence are archived into cold storage. Maintainers need automated monitoring to track TTL expiration.
- **Target Files**:
  - `app/routers/soroban.py`
  - `app/schemas/soroban.py`
  - `app/soroban/client.py`
- **Acceptance Criteria**:
  - [ ] Implement `GET /soroban/contracts/{contract_id}/ttl` endpoint returning current ledger, `liveUntilLedgerSeq`, and estimated days remaining before rent expiry.
  - [ ] Return structured 404 response when contract instance is not found on ledger.
  - [ ] Include Pydantic response schema with example payload in OpenAPI schema.

---

### Issue #15: Build Pytest Async Test Suite for Soroban Client and Scraper Modules
- **Complexity Tier**: Medium (150 Points)
- **Problem & Context**: External blockchain calls must be thoroughly mocked to guarantee test suite determinism and prevent flaky CI runs caused by external network dependencies.
- **Target Files**:
  - `tests/test_soroban_scrapers.py`
  - `tests/test_soroban_client.py`
  - `pyproject.toml`
- **Acceptance Criteria**:
  - [ ] Comprehensive async unit tests covering RPC request errors, ledger queries, and scraper ingestion.
  - [ ] 100% mock isolation using `httpx.MockTransport` or `unittest.mock.patch` with zero outbound network calls.
  - [ ] Test suite achieves overall project code coverage above 90%.

---

### Issue #16: Create Responsive Tailwind CSS Web Explorer for Soroban Contracts and Invocations
- **Complexity Tier**: Medium (150 Points)
- **Problem & Context**: Maintainers and community developers need an intuitive, responsive dashboard to explore indexed contracts, events, and health metrics directly in their browser.
- **Target Files**:
  - `app/templates/soroban_explorer.html`
  - `app/static/js/explorer.js`
  - `app/routers/soroban.py`
- **Acceptance Criteria**:
  - [ ] Responsive UI built with Jinja2 and Tailwind CSS rendering properly on mobile and desktop viewports.
  - [ ] Live search filter by Contract ID, Event Topic, and Ledger Sequence without full page reload.
  - [ ] Status indicators for contract health score and TTL rent countdown.

---

### Issue #17: Implement Server-Sent Events (SSE) Live Feed for Soroban Contract Events
- **Complexity Tier**: High (200 Points)
- **Problem & Context**: Developers building reactive dApps and monitoring bots require real-time push streams of contract event execution rather than polling REST endpoints.
- **Target Files**:
  - `app/routers/stream.py`
  - `app/main.py`
  - `tests/test_soroban_endpoints.py`
- **Acceptance Criteria**:
  - [ ] Implement `GET /soroban/stream/events` endpoint streaming event envelopes as `text/event-stream`.
  - [ ] Asynchronous generator broadcasts newly indexed events with keep-alive ping headers every 15 seconds.
  - [ ] Handles client disconnection cleanly without leaking async tasks or file descriptors.

---

### Issue #18: Build Soroban Contract WASM Bytecode Analyzer and Health Scoring Engine
- **Complexity Tier**: High (200 Points)
- **Problem & Context**: Stellar smart contracts compile to WebAssembly (WASM) with strict execution limits. Contract deployers need heuristic insights on binary footprint, export interfaces, and optimization status.
- **Target Files**:
  - `app/soroban/wasm_analyzer.py`
  - `app/routers/soroban.py`
  - `tests/test_soroban_graph_and_wasm.py`
- **Acceptance Criteria**:
  - [ ] Static bytecode analyzer inspecting binary size, export table function count, and optimization level.
  - [ ] Calculate composite health score (0–100) with actionable optimization advice.
  - [ ] Expose analysis via `GET /soroban/contracts/{contract_id}/health`.

---

### Issue #19: Develop Cross-Contract Invocation Graph Analyzer
- **Complexity Tier**: High (200 Points)
- **Problem & Context**: Complex DeFi and governance architectures on Soroban execute cross-contract calls. Maintainers need dependency visualizers to audit inter-contract coupling.
- **Target Files**:
  - `app/soroban/graph.py`
  - `app/routers/analytics.py`
  - `tests/test_soroban_graph_and_wasm.py`
- **Acceptance Criteria**:
  - [ ] Parse event histories and invocation trees to construct Directed Acyclic Graph (DAG) structures.
  - [ ] Endpoint `GET /soroban/graph` returns nodes (contract addresses) and edges (invocation weights/counts).
  - [ ] Output format is compatible with graph visualization tools (D3.js, Cytoscape.js).

---

### Issue #20: Implement Automated GitHub Actions CI for Ruff Linting, Mypy Type Checking, and Pytest
- **Complexity Tier**: High (200 Points)
- **Problem & Context**: To maintain strict software engineering standards across multi-contributor PRs, continuous integration must enforce linting, strict typing, and test coverage gates.
- **Target Files**:
  - `.github/workflows/ci.yml`
  - `pyproject.toml`
- **Acceptance Criteria**:
  - [ ] GitHub Actions workflow triggers on push to `main` and pull requests.
  - [ ] Executes `ruff check .` with zero linting warnings.
  - [ ] Executes `mypy app` with zero type errors.
  - [ ] Executes `pytest --cov=app --cov-report=term-missing --cov-fail-under=90`.
  - [ ] Enforces pip dependency caching and concurrent job cancellation for efficiency.
