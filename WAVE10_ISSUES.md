# Maintainer Issues for Drips Wave 10

## Issue #1: Add OpenAPI / FastAPI Metadata Tags & Detailed Docstrings to Soroban REST Endpoints
**Complexity Tier:** Trivial (100 Points)
**Background & Context:** The OpenAPI documentation at `/docs` lacks detailed field descriptions, tags, and realistic response examples for Soroban smart contract endpoints.
**Task Requirements:** Add Pydantic `Field(description=...)` to all Soroban schemas in `app/schemas/soroban.py`. Update `app/routers/soroban.py` with endpoint tags (`Soroban Analytics`) and docstrings.
**Acceptance Criteria:** Swagger UI at `/docs` displays full schemas, field descriptions, and 200 OK response examples for `/soroban/events` and `/soroban/contracts/{id}/metrics`.
**Target Files:** `app/schemas/soroban.py`, `app/routers/soroban.py`

## Issue #2: Implement Robust Exponential Backoff & Retry Logic for Soroban RPC Client
**Complexity Tier:** Trivial (100 Points)
**Background & Context:** Public Soroban RPC nodes occasionally experience rate limiting or transient HTTP 503 errors during high network traffic.
**Task Requirements:** Implement a retry decorator using `tenacity` or custom async exponential backoff in `app/soroban/client.py` for all HTTP RPC requests.
**Acceptance Criteria:** Transient network failures retry up to 3 times before raising a structured `SorobanRPCException`. Unit test verifies retry behavior under simulated 503 HTTP responses.
**Target Files:** `app/soroban/client.py`, `tests/test_soroban_client.py`

## Issue #3: Build Async Soroban Contract Event Ingestion Worker Using getEvents RPC
**Complexity Tier:** Medium (150 Points)
**Background & Context:** To track Soroban contract activity across Wave projects, DripsLens needs a background ingestion worker that polls Soroban RPC for new contract events.
**Task Requirements:** Write an async worker function `ingest_soroban_events()` in `app/soroban/indexer.py` that queries `getEvents` starting from the last indexed ledger sequence and stores parsed events in PostgreSQL.
**Acceptance Criteria:** New contract events are stored in `contract_events` table without duplicate entries. Worker runs smoothly on APScheduler 15-minute intervals.
**Target Files:** `app/soroban/indexer.py`, `app/scheduler/tasks.py`

## Issue #4: Develop Storage Footprint & TTL Expiry Monitoring Endpoint for Soroban Contracts
**Complexity Tier:** Medium (150 Points)
**Background & Context:** Soroban uses a rent-based storage model with Time-To-Live (TTL) expiration for ledger entries. Maintainers need visibility into when their contract storage keys expire.
**Task Requirements:** Implement `/soroban/contracts/{contract_id}/ttl` endpoint querying `getLedgerEntries` via Soroban RPC to extract `liveUntilLedgerSeq` and calculate remaining TTL days.
**Acceptance Criteria:** Endpoint returns contract ID, current ledger sequence, `liveUntilLedgerSeq`, remaining ledgers, and estimated expiration timestamp in ISO format.
**Target Files:** `app/routers/soroban.py`, `app/soroban/client.py`

## Issue #5: Build Pytest Async Test Suite for Stellar Horizon & Soroban Scrapers
**Complexity Tier:** Medium (150 Points)
**Background & Context:** Drips Wave maintainer quality criteria require automated test coverage for external API integrations.
**Task Requirements:** Create comprehensive async unit tests in `tests/test_soroban_scrapers.py` using `pytest-asyncio` and `respx` / `httpx.MockTransport` to test Horizon and Soroban RPC responses.
**Acceptance Criteria:** Test suite passes with 100% success rate and pushes overall project code coverage above 90%. Running `pytest` requires zero external network calls.
**Target Files:** `tests/test_soroban_scrapers.py`, `pyproject.toml`

## Issue #6: Create Responsive Tailwind React Dashboard Component for Soroban Event Explorer
**Complexity Tier:** Medium (150 Points)
**Background & Context:** The current Jinja2 dashboard requires an interactive UI component to allow developers to filter and inspect Soroban contract events.
**Task Requirements:** Develop a lightweight frontend component (or HTMX/Alpine.js interface) with search filters for Contract ID, Event Topic, and Date Range.
**Acceptance Criteria:** Users can filter events live on `/soroban/explorer` without full page reloads. Search results render cleanly across desktop and mobile screens.
**Target Files:** `app/templates/soroban_explorer.html`, `app/static/js/explorer.js`

## Issue #7: Implement Server-Sent Events (SSE) Endpoint for Real-Time Soroban Event Streaming
**Complexity Tier:** High (200 Points)
**Background & Context:** Developers building dApps need real-time streams of smart contract events without constantly polling the REST API.
**Task Requirements:** Implement a FastAPI Server-Sent Events (SSE) endpoint `/soroban/stream/events` using `sse-starlette` or async generators streaming newly ingested events.
**Acceptance Criteria:** Clients connecting to `/soroban/stream/events` receive real-time JSON event envelopes as soon as the background worker indexes them. Connection closes gracefully on client disconnect.
**Target Files:** `app/routers/stream.py`, `app/main.py`

## Issue #8: Build Soroban Contract WASM Bytecode Analyzer & Security Heuristic Scorer
**Complexity Tier:** High (200 Points)
**Background & Context:** Stellar smart contracts are compiled to WebAssembly (WASM) with a 64KB size limit. DripsLens should analyze contract WASM files to score codebase health.
**Task Requirements:** Create `app/soroban/wasm_analyzer.py` that fetches contract WASM bytecode, verifies size limits, checks for standard export functions, and returns a 0–100 health score.
**Acceptance Criteria:** Endpoint `/soroban/contracts/{id}/health` returns detailed health metrics, WASM size, exported functions count, and optimization recommendations.
**Target Files:** `app/soroban/wasm_analyzer.py`, `app/routers/soroban.py`

## Issue #9: Develop Cross-Contract Invocation Visualizer for Drips Wave Ecosystem Projects
**Complexity Tier:** High (200 Points)
**Background & Context:** Soroban smart contracts frequently make cross-contract invocations. Visualizing these relationships helps maintainers understand ecosystem dependencies.
**Task Requirements:** Build an analytical pipeline that analyzes contract event logs to discover cross-contract calls and outputs a Directed Acyclic Graph (DAG) JSON structure.
**Acceptance Criteria:** Endpoint `/soroban/graph` returns nodes (contracts) and edges (invocation links) compatible with D3.js or Cytoscape.js visualization.
**Target Files:** `app/soroban/graph.py`, `app/routers/analytics.py`

## Issue #10: Implement Automated GitHub Actions CI/CD Workflow with Ruff & Pytest Coverage Enforcement
**Complexity Tier:** High (200 Points)
**Background & Context:** Continuous integration is necessary to maintain code quality across open-source contributions during Drips Wave sprints.
**Task Requirements:** Create `.github/workflows/ci.yml` that runs on every push and PR to `main`. It must execute `ruff check .`, `mypy app`, and `pytest --cov=app --cov-fail-under=90`.
**Acceptance Criteria:** Pull requests automatically fail CI if code coverage drops below 90% or if linting errors exist.
**Target Files:** `.github/workflows/ci.yml`, `pyproject.toml`
