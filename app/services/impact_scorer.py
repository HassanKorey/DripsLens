"""Contributor impact scoring and cross-repository activity analysis engine.

Calculates multi-dimensional contributor impact scores across Drips Wave repositories
based on merged pull request volume, issue points, peer review activity, and repository multipliers.
"""

import math
from typing import Any


def calculate_impact_score(
    merged_prs: int,
    points_earned: int,
    review_count: int = 0,
    repo_multiplier: float = 1.0,
) -> dict[str, Any]:
    """Calculate raw and normalized contributor impact scores (0 to 100 scale).

    Formula:
        Score_raw = (merged_prs * W_prs + points_earned * W_points + review_count * W_reviews) * max(1.0, repo_multiplier)
        Score_normalized = min(100.0, max(0.0, (1.0 - exp(-Score_raw / K)) * 100.0))
    """
    w_prs = 4.0
    w_points = 0.05
    w_reviews = 3.0
    k_scaling = 120.0

    eff_multiplier = max(1.0, float(repo_multiplier))
    prs_component = round(merged_prs * w_prs, 2)
    points_component = round(points_earned * w_points, 2)
    reviews_component = round(review_count * w_reviews, 2)

    raw_score = round((prs_component + points_component + reviews_component) * eff_multiplier, 2)
    if raw_score <= 0.0:
        normalized_score = 0.0
    else:
        normalized_score = round(min(100.0, max(0.0, (1.0 - math.exp(-raw_score / k_scaling)) * 100.0)), 2)

    return {
        "impact_score": normalized_score,
        "raw_score": raw_score,
        "score_breakdown": {
            "merged_prs_component": prs_component,
            "points_component": points_component,
            "review_component": reviews_component,
            "repo_multiplier": eff_multiplier,
            "weights": {
                "merged_prs": w_prs,
                "points_earned": w_points,
                "review_count": w_reviews,
            },
        },
    }


def calculate_percentile_rank(target_score: float, all_scores: list[float]) -> float:
    """Calculate empirical percentile ranking (0.0 to 100.0) relative to contributor peer population."""
    if not all_scores:
        return 100.0
    le_count = sum(1 for score in all_scores if score <= target_score)
    return round((le_count / len(all_scores)) * 100.0, 1)
