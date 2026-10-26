# 📡 API Reference

Complete endpoint specification for DripsLens REST API and real-time streaming services.

---

## Base URLs

- **Production Live URL**: `https://dripslens.onrender.com`
- **Interactive Swagger Docs**: `https://dripslens.onrender.com/docs`
- **ReDoc Schema**: `https://dripslens.onrender.com/redoc`

---

## 1. System Health

### `GET /health`
Returns system status, application version, database connectivity, and background scheduler state.

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "app": "DripsLens",
  "version": "2.0.0",
  "uptime_seconds": 1845.2104,
  "timestamp": "2026-10-26T12:00:00.000000+00:00",
  "database": "connected",
  "scheduler": "running"
}
```

---

## 2. Repositories

### `GET /repos`
List tracked Drips Wave repositories with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `language` | `string` | Optional | Filter by programming language (e.g., `Python`, `Rust`) |
| `multiplier`| `integer`| Optional | Filter by wave multiplier (e.g., `1`, `2`) |
| `skip` | `integer`| Optional | Number of items to skip (Default: `0`) |
| `limit` | `integer`| Optional | Maximum items to return, 1–100 (Default: `10`) |

**Response (`200 OK`):**
```json
[
  {
    "id": 1,
    "name": "HassanKorey/DripsLens",
    "language": "Python",
    "multiplier": 2,
    "issue_count": 12,
    "health_score": 98,
    "is_verified": true
  }
]
```

---

### `GET /repos/{repo_id}/health`
Retrieve detailed health score metrics and verification status for a specific repository.

**Path Parameters:**
- `repo_id` (`integer`): Repository ID.

**Response (`200 OK`):**
```json
{
  "repo_id": 1,
  "health_score": 98,
  "is_verified": true
}
```

---

## 3. Issues & Bounties

### `GET /issues`
List bounty issues filtered by complexity tier and claim status.

**Query Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `complexity` | `string` | Optional | `Trivial` (100 pts), `Medium` (150 pts), or `High` (200 pts) |
| `is_claimed` | `boolean`| Optional | Filter by claimed status (`true` / `false`) |
| `skip` | `integer`| Optional | Number of items to skip (Default: `0`) |
| `limit` | `integer`| Optional | Maximum items to return, 1–100 (Default: `10`) |

**Response (`200 OK`):**
```json
[
  {
    "id": 1,
    "title": "docs(openapi): enrich OpenAPI route metadata and filter query parameter examples",
    "url": "https://github.com/HassanKorey/DripsLens/issues/1",
    "repo_id": 1,
    "complexity": "Trivial",
    "points": 100,
    "is_claimed": false
  }
]
```

---

## 4. Leaderboard & Contributors

### `GET /leaderboard` (or `/contributors/top`)
Returns top ecosystem contributors ranked by points earned and merged pull requests.

**Query Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `limit` | `integer`| Optional | Maximum contributors to retrieve (Default: `10`) |

**Response (`200 OK`):**
```json
[
  {
    "id": 1,
    "github_username": "HassanKorey",
    "merged_prs": 18,
    "points_earned": 2700
  },
  {
    "id": 2,
    "github_username": "HirthikBalaji",
    "merged_prs": 4,
    "points_earned": 600
  }
]
```

---

## 5. Soroban Smart Contracts

### `GET /soroban/events`
Fetch indexed contract event envelopes with topic filtering.

### `GET /soroban/contracts/{contract_id}/metrics`
Retrieve contract bytecode metrics and health score evaluation.

### `GET /soroban/contracts/{contract_id}/ttl`
Calculate state storage rent expiration sequence and remaining active days.

### `GET /soroban/graph`
Retrieve inter-contract invocation DAG nodes and directed edges for visualization.

---

## 6. Real-Time Streaming

### `GET /soroban/stream/events`
Server-Sent Events (SSE) broadcast delivering contract events in real-time.

**Headers:**
- `Accept: text/event-stream`

**Stream Example:**
```text
data: {"id": "evt_stream", "topic": "transfer", "amount": 100}

data: {"id": "evt_stream", "topic": "approval", "owner": "GA..."}
```
