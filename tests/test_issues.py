"""Tests for the /issues API."""

from tests.conftest import *  # noqa: F401,F403


def test_list_issues(client, seed_repos):
    resp = client.get("/issues")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["items"][0]["repo"] == "stellar/soroban-examples"


def test_list_issues_filter_complexity(client, seed_repos):
    resp = client.get("/issues", params={"complexity": "trivial"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["points"] == 100


def test_list_issues_filter_claimed(client, seed_repos):
    unclaimed = client.get("/issues", params={"claimed": "false"}).json()
    claimed = client.get("/issues", params={"claimed": "true"}).json()
    assert unclaimed["total"] == 1
    assert claimed["total"] == 1
    assert claimed["items"][0]["assignees"] == ["octocat"]


def test_issue_stats(client, seed_repos):
    resp = client.get("/issues/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["open_issues"] == 2
    assert stats["claimed"] == 1
    assert stats["unclaimed"] == 1
    assert stats["potential_points"] == 250
