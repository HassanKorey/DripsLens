"""Integration and unit tests for CSV/JSON ecosystem data export endpoints (/export/repos, /export/contributors)."""

import csv
import io
import json

import pytest

from app.models.contributor import Contributor
from app.models.repo import Repo
from app.routers.export import sanitize_csv_field


def test_sanitize_csv_field_prevents_formula_injection():
    """Verify CSV formula prefixes (=, +, -, @) are prefixed with a single quote."""
    assert sanitize_csv_field("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert sanitize_csv_field("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert sanitize_csv_field("-1+1") == "'-1+1"
    assert sanitize_csv_field("@IMPORTXML()") == "'@IMPORTXML()"
    assert sanitize_csv_field("HassanKorey/DripsLens\nNext") == "HassanKorey/DripsLens Next"
    assert sanitize_csv_field(None) == ""
    assert sanitize_csv_field(98) == 98


@pytest.mark.asyncio
async def test_export_repos_json_and_csv(async_client, seed_drips_data):
    """GET /export/repos supports both format=json and format=csv with Content-Disposition headers."""
    resp_json = await async_client.get("/export/repos?format=json")
    assert resp_json.status_code == 200
    assert resp_json.headers["content-disposition"] == 'attachment; filename="repos.json"'
    assert "application/json" in resp_json.headers["content-type"]

    data = json.loads(resp_json.text)
    assert len(data) == 2
    assert data[0]["name"] == "HassanKorey/DripsLens"
    assert data[0]["language"] == "Python"
    assert data[0]["is_verified"] is True

    resp_csv = await async_client.get("/export/repos?format=csv")
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-disposition"] == 'attachment; filename="repos.csv"'
    assert "text/csv" in resp_csv.headers["content-type"]

    reader = list(csv.DictReader(io.StringIO(resp_csv.text)))
    assert len(reader) == 2
    assert reader[0]["name"] == "HassanKorey/DripsLens"
    assert reader[0]["language"] == "Python"
    assert reader[1]["name"] == "stellar/soroban-example-dapp"


@pytest.mark.asyncio
async def test_export_repos_language_filter_and_csv_sanitization(async_client, db_session):
    """Verify language filtering and CSV field sanitization on malicious repository names."""
    malicious_repo = Repo(
        id=10,
        name="=HYPERLINK(\"http://evil.example\",\"click\")",
        language="Rust",
        multiplier=2,
        issue_count=3,
        health_score=90,
        is_verified=False,
    )
    db_session.add(malicious_repo)
    await db_session.commit()

    resp_csv = await async_client.get("/export/repos?format=csv&language=rust")
    assert resp_csv.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp_csv.text)))
    assert len(rows) == 1
    assert rows[0]["name"].startswith("'=HYPERLINK")


@pytest.mark.asyncio
async def test_export_contributors_json_and_csv(async_client, seed_drips_data, db_session):
    """GET /export/contributors orders by points_earned desc and streams valid CSV and JSON."""
    formula_user = Contributor(
        id=99,
        github_username="@formula_actor",
        merged_prs=1,
        points_earned=100,
    )
    db_session.add(formula_user)
    await db_session.commit()

    resp_json = await async_client.get("/export/contributors?format=json")
    assert resp_json.status_code == 200
    assert resp_json.headers["content-disposition"] == 'attachment; filename="contributors.json"'
    records = json.loads(resp_json.text)
    assert len(records) == 3
    assert records[0]["github_username"] == "HassanKorey"
    assert records[0]["points_earned"] == 2700

    resp_csv = await async_client.get("/export/contributors?format=csv")
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-disposition"] == 'attachment; filename="contributors.csv"'
    rows = list(csv.DictReader(io.StringIO(resp_csv.text)))
    assert len(rows) == 3
    assert rows[0]["github_username"] == "HassanKorey"
    assert rows[2]["github_username"] == "'@formula_actor"


@pytest.mark.asyncio
async def test_export_invalid_format_rejected(async_client):
    """Invalid format query parameter returns HTTP 422 validation error."""
    resp = await async_client.get("/export/repos?format=xml")
    assert resp.status_code == 422
