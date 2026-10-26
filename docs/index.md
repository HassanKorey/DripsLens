# 💧 DripsLens Documentation

> **Real-Time Analytics Engine & Search Platform for the Drips Wave Ecosystem**

Welcome to the official developer documentation for **DripsLens**. DripsLens makes the Drips Wave ecosystem trackable, searchable, and verifiable by providing real-time indexing of Soroban smart contract events, repository signal tracking, contributor leaderboard ranking, WASM bytecode health scoring, and state storage TTL monitoring.

---

## 🚀 Quick Navigation

<div class="grid cards" markdown>

-   :material-pillar:{ .lg .middle } **[System Architecture](architecture.md)**

    ---

    Explore the high-level monorepo design, FastAPI routes, async worker processes, and database layout.

-   :material-pipe:{ .lg .middle } **[Ingestion Pipeline](ingestion-pipeline.md)**

    ---

    Deep dive into Soroban RPC polling, GitHub REST API client, Horizon verification, and tenacity retries.

-   :material-database:{ .lg .middle } **[Data Models](data-models.md)**

    ---

    Inspect the SQLAlchemy 2.0 async relational schemas: repos, issues, contributors, contracts, and events.

-   :material-api:{ .lg .middle } **[API Reference](api-reference.md)**

    ---

    Detailed specification of public REST endpoints, query filters, pagination, and Server-Sent Events (SSE).

</div>

---

## ⚡ Key Capabilities

- **Stellar Horizon & Soroban Ingestion**: Resilient background workers polling JSON-RPC 2.0 (`getEvents`, `getHealth`) and REST APIs with exponential backoff.
- **Fault-Tolerant Rate Limiting**: Tenacity retry policies handling HTTP 429 and 503 errors gracefully with dynamic `Retry-After` header extraction.
- **Automated Database Migrations**: Seamless schema provisioning and upgrades via `alembic upgrade head` across PostgreSQL and SQLite.
- **WASM Bytecode Health Engine**: Inspects contract footprint, size thresholds, and function exports to generate actionable health scores (0–100).
- **Time-to-Live (TTL) Rent Boundaries**: Proactively computes remaining live days until contract instance archival to alert developers.
- **DAG Invocation Topology**: Discovers inter-contract call graphs and outputs node/edge graph data for topological analysis.
- **Live Event Streaming (SSE)**: Real-time broadcast channel powered by `sse-starlette` for monitoring agents and dashboard UIs.

---

## 🌐 Live Deployments

| Resource | Target URL | Description |
| :--- | :--- | :--- |
| **Search Portal** | [`https://dripslens.onrender.com`](https://dripslens.onrender.com) | Production web dashboard |
| **Interactive API Docs (Swagger UI)** | [`https://dripslens.onrender.com/docs`](https://dripslens.onrender.com/docs) | OpenAPI interactive explorer |
| **Alternative Docs (ReDoc)** | [`https://dripslens.onrender.com/redoc`](https://dripslens.onrender.com/redoc) | ReDoc schema viewer |
| **System Health Probe** | [`https://dripslens.onrender.com/health`](https://dripslens.onrender.com/health) | Uptime and connectivity telemetry |
| **Documentation Portal** | [`https://HassanKorey.github.io/DripsLens`](https://HassanKorey.github.io/DripsLens) | GitHub Pages technical guides |

---

## 🛠 Tech Stack

- **Runtime**: Python 3.12+
- **API Framework**: FastAPI & Starlette
- **Async ORM**: SQLAlchemy 2.0 (Asyncpg & Aiosqlite)
- **Migrations**: Alembic
- **Task Scheduling**: APScheduler (AsyncIOScheduler)
- **Resilience Engine**: Tenacity
- **Caching**: Redis
- **Real-Time Streaming**: SSE-Starlette
- **Blockchain Connectivity**: Stellar SDK & Soroban RPC 2.0
