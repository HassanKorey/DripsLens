"""Unit and integration tests for contributor impact scoring engine and analytics router."""

import pytest
from httpx import AsyncClient

from app.services.impact_scorer import calculate_impact_score, calculate_percentile_rank


def test_calculate_impact_score_zero():
    """Zero contributions return zero impact score."""
    metrics = calculate_impact_score(0, 0, 0, 1.0)
    assert metrics["impact_score"] == 0.0
    assert metrics["raw_score"] == 0.0
    assert metrics["score_breakdown"]["merged_prs_component"] == 0.0


def test_calculate_impact_score_normalization_bounds():
    """Impact scores must stay normalized strictly within 0 to 100 range even with massive metrics."""
    normal = calculate_impact_score(5, 500, 2, 1.0)
    assert 0.0 <= normal["impact_score"] <= 100.0

    massive = calculate_impact_score(500, 100000, 200, 3.0)
    assert massive["impact_score"] <= 100.0
    assert massive["impact_score"] >= 99.0


def test_calculate_percentile_rank():
    """Empirical percentile ranking behaves accurately with mock population."""
    scores = [10.0, 25.0, 50.0, 75.0, 90.0]
    assert calculate_percentile_rank(90.0, scores) == 100.0
    assert calculate_percentile_rank(50.0, scores) == 60.0
    assert calculate_percentile_rank(5.0, scores) == 0.0
    assert calculate_percentile_rank(50.0, []) == 100.0


@pytest.mark.asyncio
async def test_get_contributor_impact_endpoint(async_client: AsyncClient, seed_drips_data):
    """GET /analytics/contributors/{username}/impact returns accurate score, breakdown, and percentile."""
    resp = await async_client.get("/analytics/contributors/HassanKorey/impact?review_count=3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["username"] == "HassanKorey"
    assert 0.0 <= data["impact_score"] <= 100.0
    assert "score_breakdown" in data
    assert data["activity_metrics"]["merged_prs"] == 18
    assert data["activity_metrics"]["points_earned"] == 2700
    assert data["activity_metrics"]["review_count"] == 3
    assert data["percentile_ranking"] >= 50.0
    assert len(data["history"]) > 0


@pytest.mark.asyncio
async def test_get_contributor_impact_not_found(async_client: AsyncClient, seed_drips_data):
    """GET /analytics/contributors/{username}/impact returns 404 for non-existent user."""
    resp = await async_client.get("/analytics/contributors/non_existent_user_xyz/impact")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
