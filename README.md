# 💧 DripsLens

<div align="center">

**Next-Generation Soroban Smart Contract & Stellar Analytics Engine**

[![CI](https://github.com/HassanKorey/DripsLens/actions/workflows/ci.yml/badge.svg)](https://github.com/HassanKorey/DripsLens/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Soroban RPC](https://img.shields.io/badge/Soroban-RPC%20v2.0-8A2BE2.svg)](https://soroban.stellar.org/)
[![Stellar Horizon](https://img.shields.io/badge/Stellar-Horizon%20API-black.svg?logo=stellar&logoColor=white)](https://developers.stellar.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: Mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-80%25%2B-brightgreen.svg)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Quickstart](#-getting-started) •
[API Reference](#-api-reference) •
[Configuration](#-configuration--environment-variables) •
[Testing](#-testing--code-quality) •
[Deployment](#-deployment) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

**DripsLens** is a high-performance, asynchronous analytics and indexing engine designed specifically for the **Stellar** blockchain and **Soroban** smart contracts ecosystem. Built with Python 3.10+ and FastAPI, DripsLens bridges the gap between on-chain contract events and real-time developer observability.

DripsLens automates the ingestion of Soroban event logs, evaluates compiled WebAssembly (WASM) bytecode health and footprint, monitors state storage Time-To-Live (TTL) rent boundaries to prevent state archival, resolves cross-contract invocation dependencies into directed graphs (DAG), and streams real-time contract execution feeds directly to web clients.

---

## ⚡ Key Features

- **🔮 Soroban RPC Event Indexing**: Automated, resilient background worker that periodically polls JSON-RPC 2.0 endpoints (`getEvents`) with exponential backoff and error recovery, persisting event envelopes into asynchronous relational storage.
- **🔬 WASM Bytecode Analyzer & Health Scoring**: Static byte analysis inspecting size thresholds, function exports, and contract footprint to calculate health scores (0–100) and optimization recommendations.
- **⏳ Contract State Storage & TTL Tracking**: Monitors ledger expiration sequences (`liveUntilLedgerSeq`) and computes remaining live days to alert maintainers before contract instance rent expires.
- **🕸️ Cross-Contract Invocation Graph (DAG)**: Discovers and maps inter-contract calls from event histories, outputting Directed Acyclic Graph topology nodes and edges for visual dependency analysis.
- **📡 Real-Time Live Event Streaming (SSE)**: Built-in Server-Sent Events endpoint powered by `sse-starlette` providing low-latency event broadcasts to client dashboards, monitoring agents, and bots.
- **🛡️ Stellar Horizon Account & SAC Verification**: Validates public key addresses, Stellar Asset Contracts (SAC), and account balances directly against the Stellar Horizon REST API.
- **⚡ High-Throughput Resilient Caching**: Non-blocking caching layer powered by Redis with transparent in-memory and error-safe fallbacks, preventing database pressure during traffic spikes.
- **📊 Interactive Web Explorer**: Modern responsive UI built with Jinja2 and Tailwind CSS for real-time visualization of indexed contract telemetry.

---

## 🏛 System Architecture

The following diagram illustrates how clients, API endpoints, background schedulers, storage engines, and external blockchain nodes interact within DripsLens:

```mermaid
flowchart TD
    subgraph Clients["Consumers & Web Clients"]
        UI["Web Dashboard (/soroban/explorer)"]
        Consumer["dApps / API Consumers / Bots"]
        SSEClient["Event Stream Consumers"]
    end

    subgraph FastAPILayer["DripsLens FastAPI Core (app/main.py)"]
        RouterSoroban["Soroban Router (/soroban)"]
        RouterAnalytics["Analytics Router (/soroban/graph)"]
        RouterStream["SSE Stream Router (/soroban/stream)"]
    end

    subgraph CacheAndServices["Services & Resilience Layer"]
        RedisCache["Redis Cache Layer (app/cache)"]
        WasmAnalyzer["WASM Analyzer (app/soroban/wasm_analyzer)"]
        GraphEngine["DAG Graph Engine (app/soroban/graph)"]
        RPCClient["Soroban RPC Client (httpx + tenacity)"]
        HorizonClient["Stellar Horizon Verifier (app/scrapers)"]
    end

    subgraph BackgroundWorkers["Background Processing (APScheduler)"]
        Scheduler["AsyncIOScheduler (app/scheduler)"]
        Indexer["Event Indexer Worker (app/soroban/indexer)"]
    end

    subgraph DataStorage["Data Storage"]
        DB[(PostgreSQL / SQLite with SQLAlchemy 2.0 Async)]
    end

    subgraph StellarEcosystem["Stellar Blockchain & Soroban Network"]
        SorobanNode["Soroban RPC Node (JSON-RPC 2.0)"]
        HorizonNode["Stellar Horizon REST API"]
    end

    %% Client Interactions
    UI --> RouterSoroban
    Consumer --> RouterSoroban
    Consumer --> RouterAnalytics
    SSEClient --> RouterStream

    %% Router to Services
    RouterSoroban --> RedisCache
    RouterSoroban --> WasmAnalyzer
    RouterAnalytics --> GraphEngine
    RouterSoroban --> DB
    RedisCache -.-> DB

    %% Background Engine Interactions
    Scheduler --> Indexer
    Indexer --> RPCClient
    Indexer --> DB

    %% External Blockchain Integrations
    RPCClient --> SorobanNode
    HorizonClient --> HorizonNode
```

---

## 🧰 Tech Stack

| Domain | Technologies & Libraries |
| :--- | :--- |
| **Framework & Web** | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Starlette](https://www.starlette.io/), [SSE-Starlette](https://github.com/sysid/sse-starlette) |
| **Language & Typing** | [Python 3.10+](https://www.python.org/), [Pydantic v2](https://docs.pydantic.dev/), [Pydantic-Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| **Database & ORM** | [PostgreSQL 15](https://www.postgresql.org/), [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/), [asyncpg](https://github.com/MagicStack/asyncpg), [aiosqlite](https://github.com/omnilib/aiosqlite), [Alembic](https://alembic.sqlalchemy.org/) |
| **Caching Layer** | [Redis 7](https://redis.io/), [redis-py](https://github.com/redis/redis-py) (with graceful in-memory degradation) |
| **Blockchain / Web3** | [Stellar Python SDK](https://github.com/StellarCN/py-stellar-base), Soroban JSON-RPC 2.0, Stellar Horizon API |
| **HTTP & Resilience** | [HTTPX](https://www.python-httpx.org/), [Tenacity](https://tenacity.readthedocs.io/) (exponential backoff & retry) |
| **Task Scheduling** | [APScheduler](https://apscheduler.readthedocs.io/) (`AsyncIOScheduler`) |
| **Frontend & Templates** | [Jinja2](https://jinja.palletsprojects.com/), [Tailwind CSS](https://tailwindcss.com/) |
| **Testing & Quality** | [Pytest](https://pytest.org/), [Pytest-Asyncio](https://github.com/pytest-dev/pytest-asyncio), [Pytest-Cov](https://github.com/pytest-dev/pytest-cov), [Ruff](https://astral.sh/ruff), [Mypy](https://mypy-lang.org/) |
| **DevOps & Containers** | [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/), [Render](https://render.com/) |

---

## 📂 Project Structure

```text
DripsLens/
├── app/
│   ├── cache/                  # Caching layer
│   │   └── redis_client.py     # Redis client & @cache_response decorator with fallback
│   ├── db/                     # Database access & migrations
│   │   ├── database.py         # SQLAlchemy async engine & session generator
│   │   └── migrations/         # Alembic database revision scripts
│   ├── models/                 # SQLAlchemy ORM models
│   │   └── soroban.py          # SorobanContract, ContractEvent, StorageMetric
│   ├── routers/                # FastAPI endpoint controllers
│   │   ├── analytics.py        # /soroban/graph DAG invocation endpoint
│   │   ├── soroban.py          # /soroban/events, /metrics, /ttl, /health
│   │   └── stream.py           # /soroban/stream/events SSE live stream
│   ├── scheduler/              # Asynchronous scheduling engine
│   │   └── tasks.py            # APScheduler setup & recurring indexing jobs
│   ├── schemas/                # Pydantic serialization & validation schemas
│   │   └── soroban.py          # ContractEventSchema, SorobanContractSchema
│   ├── scrapers/               # External blockchain verification
│   │   └── stellar.py          # Stellar Horizon account & SAC validation
│   ├── soroban/                # Soroban domain logic & RPC clients
│   │   ├── client.py           # JSON-RPC 2.0 client with tenacity retry policies
│   │   ├── graph.py            # Cross-contract invocation DAG generator
│   │   ├── indexer.py          # Background polling & event envelope ingestion
│   │   └── wasm_analyzer.py    # Bytecode analyzer & health scoring
│   ├── static/                 # Static assets (CSS, JS)
│   ├── templates/              # Jinja2 dashboard templates
│   │   └── soroban_explorer.html # Interactive event explorer UI
│   ├── config.py               # Application settings & environment loader
│   └── main.py                 # FastAPI application factory & router mounting
├── tests/                      # Automated test suite
│   ├── conftest.py             # Pytest fixtures & isolated async SQLite DB
│   ├── test_cache.py           # Redis cache decorator tests
│   ├── test_config.py          # Configuration loading tests
│   ├── test_database.py        # Database ORM CRUD tests
│   ├── test_scrapers.py        # Stellar Horizon verification tests
│   ├── test_soroban_client.py  # Soroban JSON-RPC client tests
│   ├── test_soroban_endpoints.py # API router & SSE streaming tests
│   ├── test_soroban_graph_and_wasm.py # DAG builder & WASM analyzer tests
│   └── test_soroban_scrapers.py# Indexer & scraper task tests
├── .env.example                # Example environment variables template
├── .github/workflows/ci.yml    # GitHub Actions CI pipeline
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Docker Compose multi-service definition
├── Dockerfile                  # Production container definition
├── pyproject.toml              # Project metadata & tool configurations (Ruff, Mypy, Pytest)
├── render.yaml                 # Render cloud deployment blueprint
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

---

## 📋 Prerequisites

Before setting up DripsLens locally, ensure you have the following installed:

- **Python**: `>= 3.10`
- **Git**: `>= 2.30`
- **Docker & Docker Compose** *(optional, recommended for full-stack deployment)*
- **PostgreSQL 15+** & **Redis 7+** *(optional for containerized setup; local testing uses SQLite)*

---

## 🚀 Getting Started

You can run DripsLens either via **Docker Compose** (recommended for a full production-like environment) or directly in a **Local Virtual Environment**.

### Option A: Running with Docker Compose (Recommended)

Docker Compose starts the FastAPI application, PostgreSQL database, and Redis cache in synchronized containers:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HassanKorey/DripsLens.git
   cd DripsLens
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Build and start services:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify running containers:**
   ```bash
   docker-compose ps
   ```

5. **Access the application:**
   - **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Alternative API Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Soroban Event Explorer Dashboard**: [http://localhost:8000/soroban/explorer](http://localhost:8000/soroban/explorer)

6. **View logs or stop services:**
   ```bash
   # View streaming logs
   docker-compose logs -f app

   # Stop all services
   docker-compose down
   ```

---

### Option B: Local Virtual Environment Setup

For local development and testing:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HassanKorey/DripsLens.git
   cd DripsLens
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up your environment variables:**
   ```bash
   cp .env.example .env
   ```
   *(For quick local development without Postgres or Redis, DripsLens automatically supports in-memory SQLite and in-process fallback caching).*

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Launch the development server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Open in browser:**
   - Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.
   - Visit [http://localhost:8000/soroban/explorer](http://localhost:8000/soroban/explorer) for the Event Explorer.

---

## ⚙️ Configuration & Environment Variables

DripsLens uses Pydantic Settings to load and validate configurations from environment variables or a `.env` file:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `string` | `sqlite:///./dripslens.db` | SQLAlchemy connection string (`postgresql+asyncpg://...` or `sqlite+aiosqlite://...`) |
| `REDIS_URL` | `string` | `""` | Redis connection URL (`redis://localhost:6379/0`). If empty, uses fail-safe in-process caching |
| `CACHE_TTL_SECONDS` | `integer` | `300` | Default time-to-live for cached responses in seconds |
| `SOROBAN_RPC_URL` | `string` | `https://soroban-testnet.stellar.org:443` | JSON-RPC 2.0 endpoint for Soroban network interactions |
| `STELLAR_HORIZON_URL` | `string` | `https://horizon-testnet.stellar.org` | Stellar Horizon API endpoint for account & asset verifications |
| `STELLAR_RPC_URL` | `string` | `""` | Optional secondary Soroban RPC URL for smart contract verification |
| `REFRESH_INTERVAL_HOURS`| `float` | `6.0` | Refresh interval interval for background synchronization tasks |
| `SCHEDULER_ENABLED` | `boolean` | `true` | Enables or disables background APScheduler indexing jobs |
| `INITIAL_REFRESH_ON_STARTUP` | `boolean` | `true` | Triggers an immediate indexing cycle upon application startup |
| `ADMIN_TOKEN` | `string` | `""` | Secret key required to access privileged administrative trigger endpoints |
| `GITHUB_TOKEN` | `string` | `""` | Optional personal access token for GitHub API integration |
| `DEBUG` | `boolean` | `false` | Enables verbose debug logging |
| `APP_NAME` | `string` | `DripsLens` | Service name displayed in OpenAPI documentation |
| `APP_VERSION` | `string` | `0.1.0` | Semantic version string |

---

## 📡 API Reference

Interactive OpenAPI documentation is generated automatically by FastAPI and accessible at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

### Endpoints Overview

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/soroban/events` | Retrieve indexed Soroban smart contract events | `List[ContractEventSchema]` |
| `GET` | `/soroban/contracts/{contract_id}/metrics` | Fetch contract execution metrics & WASM size | `JSON` |
| `GET` | `/soroban/contracts/{contract_id}/ttl` | Retrieve contract Time-To-Live (TTL) & rent expiry | `JSON` |
| `GET` | `/soroban/contracts/{contract_id}/health` | Retrieve WASM analyzer health score & recommendations | `JSON` |
| `GET` | `/soroban/graph` | Build cross-contract invocation Directed Acyclic Graph (DAG) | `JSON` |
| `GET` | `/soroban/stream/events` | Server-Sent Events (SSE) live event broadcast stream | `text/event-stream` |
| `GET` | `/soroban/explorer` | Interactive HTML dashboard for contract event exploration | `text/html` |

---

### API Request & Response Examples

#### 1. Fetch Indexed Soroban Events
```bash
curl -X GET "http://localhost:8000/soroban/events" \
  -H "Accept: application/json"
```

**Response (`200 OK`):**
```json
[
  {
    "id": "evt_1",
    "contract_id": "CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
    "topic": "transfer",
    "data": {
      "amount": 100,
      "from": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
      "to": "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
    },
    "ledger_sequence": 12345
  }
]
```

#### 2. Get Contract Health & WASM Analysis
```bash
curl -X GET "http://localhost:8000/soroban/contracts/CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW/health" \
  -H "Accept: application/json"
```

**Response (`200 OK`):**
```json
{
  "contract_id": "CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
  "health_score": 95,
  "exported_functions": 5
}
```

#### 3. Get Contract TTL & State Expiration
```bash
curl -X GET "http://localhost:8000/soroban/contracts/CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW/ttl" \
  -H "Accept: application/json"
```

**Response (`200 OK`):**
```json
{
  "contract_id": "CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
  "liveUntilLedgerSeq": 999999,
  "remaining_days": 30
}
```

#### 4. Cross-Contract Invocation Topology Graph
```bash
curl -X GET "http://localhost:8000/soroban/graph" \
  -H "Accept: application/json"
```

**Response (`200 OK`):**
```json
{
  "nodes": [
    { "id": "CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW" },
    { "id": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC" }
  ],
  "edges": [
    {
      "source": "CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
      "target": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      "call_count": 14
    }
  ]
}
```

#### 5. Stream Real-Time Events (Server-Sent Events)
```bash
curl -N -H "Accept: text/event-stream" "http://localhost:8000/soroban/stream/events"
```

**Stream Output:**
```text
data: {"id": "evt_stream", "topic": "ping"}

data: {"id": "evt_stream", "topic": "ping"}
```

---

## 🧪 Testing & Code Quality

DripsLens enforces strict code formatting, typing rules, and a minimum **80% test coverage threshold** enforced in CI.

### Running the Test Suite
Tests execute against an isolated in-memory asynchronous SQLite engine with pre-seeded fixtures:

```bash
# Run all tests
pytest

# Run tests with coverage report and fail-under threshold
pytest --cov=app --cov-fail-under=80

# Run specific test suite
pytest tests/test_soroban_endpoints.py -v
```

### Static Analysis & Type Checking

```bash
# Fast linting and import sorting with Ruff
ruff check .

# Check formatting
ruff format --check .

# Static type checking with Mypy
mypy app
```

### Continuous Integration (CI)
Our GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push and pull request to the `main` branch, executing:
1. `ruff check .`
2. `mypy app`
3. `pytest --cov=app --cov-fail-under=80`

---

## 🚢 Deployment

### Production Docker Container
DripsLens includes a multi-stage optimized `Dockerfile`:

```bash
# Build production image
docker build -t dripslens:latest .

# Run container standalone
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/dripslens" \
  -e REDIS_URL="redis://host:6379/0" \
  --name dripslens \
  dripslens:latest
```

### Cloud Deployment with Render
A production blueprint is provided in `render.yaml`. It automatically provisions:
- A Python 3.11 web service with automatic Alembic migrations (`alembic upgrade head && uvicorn app.main:app`).
- A managed PostgreSQL instance (`drips-lens-db`).

To deploy on Render:
1. Fork or push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com/), choose **Blueprints** -> **New Blueprint Instance**.
3. Connect your repository; Render will automatically detect `render.yaml` and configure the database and web service.

---

## 🤝 Contributing

We welcome contributions from the community! To contribute:

1. Fork the repository and create your feature branch from `main`:
   ```bash
   git checkout -b feat/stellar-event-filter
   ```
2. Adhere to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:
   - `feat: add filter by contract event topic`
   - `fix(indexer): handle soroban RPC rate limiting`
   - `docs: update API reference examples`
   - `test: add coverage for TTL edge cases`
3. Ensure all tests pass with code coverage >= 80%:
   ```bash
   pytest --cov=app --cov-fail-under=80
   ```
4. Ensure linting and typing checks pass:
   ```bash
   ruff check . && mypy app
   ```
5. Submit a pull request detailing your changes.

Please review our [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for full community guidelines.

---

## 🔒 Security

For details on reporting security vulnerabilities, please refer to our [SECURITY.md](SECURITY.md). All reports are investigated promptly by the maintainers.

---

## 👥 Maintainers

- **DripsLens Maintainer Team** ([MAINTAINERS.md](MAINTAINERS.md))

---

## 📄 License

This project is open-source and distributed under the terms of the **MIT License**. See the [LICENSE](LICENSE) file for more information.
