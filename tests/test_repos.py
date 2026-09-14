"""Tests for the /repos API."""

from tests.conftest import *  # noqa: F401,F403


def test_list_repos(client, seed_repos):
    resp = client.get("/repos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    names = [item["full_name"] for item in data["items"]]
    assert "stellar/soroban-examples" in names
    # default sort health desc: first item should be the healthiest
    assert data["items"][0]["health_score"] >= data["items"][-1]["health_score"]


def test_list_repos_filter_language(client, seed_repos):
    resp = client.get("/repos", params={"language": "Rust"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["language"] == "Rust"


def test_list_repos_filter_multiplier(client, seed_repos):
    resp = client.get("/repos", params={"multiplier": 4})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["point_multiplier"] == 4.0


def test_list_repos_pagination(client, seed_repos):
    resp = client.get("/repos", params={"page": 1, "per_page": 2})
    data = resp.json()
    assert data["per_page"] == 2
    assert len(data["items"]) <= 2


def test_get_repo_by_id(client, seed_repos):
    resp = client.get("/repos/1")
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "stellar/soroban-examples"


def test_get_repo_by_name(client, seed_repos):
    resp = client.get("/repos/acme/cool-python-app")
    assert resp.status_code == 200
    assert resp.json()["id"] == 2


def test_get_repo_404(client, seed_repos):
    resp = client.get("/repos/does/not-exist")
    assert resp.status_code == 404


def test_repo_health_breakdown(client, seed_repos):
    resp = client.get("/repos/1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "health_score" in body
    assert set(body["components"]) == {"issues_available", "ci", "recency", "readme"}
