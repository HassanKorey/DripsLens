"""Unit tests for standalone DripsLens CLI client."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from app.cli import DripsLensCLI, build_parser, format_table


def test_format_table_empty():
    assert format_table(["A", "B"], []) == "No records found."


def test_format_table_aligned():
    headers = ["Name", "Score"]
    rows = [["Alice", "100"], ["Bob", "95"]]
    output = format_table(headers, rows)
    assert "Alice" in output
    assert "Score" in output
    assert "-" in output


def test_build_parser_subcommands():
    parser = build_parser()
    args_repos = parser.parse_args(["repos", "--language", "Python", "--limit", "5"])
    assert args_repos.command == "repos"
    assert args_repos.language == "Python"
    assert args_repos.limit == 5

    args_issues = parser.parse_args(["issues", "--complexity", "High", "--unclaimed"])
    assert args_issues.command == "issues"
    assert args_issues.complexity == "High"
    assert args_issues.is_claimed is False

    args_lead = parser.parse_args(["leaderboard", "--limit", "3", "--json"])
    assert args_lead.command == "leaderboard"
    assert args_lead.limit == 3
    assert args_lead.json is True

    args_search = parser.parse_args(["search", "Soroban"])
    assert args_search.command == "search"
    assert args_search.query == "Soroban"


@patch("httpx.Client.get")
def test_cmd_repos(mock_get, capsys):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {
            "id": 1,
            "name": "HassanKorey/DripsLens",
            "language": "Python",
            "multiplier": 2,
            "issue_count": 5,
            "health_score": 98,
            "is_verified": True,
        }
    ]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_resp

    cli = DripsLensCLI(base_url="http://test")
    parser = build_parser()
    args = parser.parse_args(["repos"])
    cli.cmd_repos(args)

    captured = capsys.readouterr()
    assert "HassanKorey/DripsLens" in captured.out
    assert "Python" in captured.out
    assert "98%" in captured.out


@patch("httpx.Client.get")
def test_cmd_issues_json(mock_get, capsys):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {
            "id": 1,
            "title": "Add health monitor",
            "complexity": "Trivial",
            "points": 100,
            "is_claimed": False,
            "url": "https://github.com/...",
        }
    ]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_resp

    cli = DripsLensCLI(base_url="http://test")
    parser = build_parser()
    args = parser.parse_args(["issues", "--json"])
    cli.cmd_issues(args)

    captured = capsys.readouterr()
    assert '"title": "Add health monitor"' in captured.out


@patch("httpx.Client.get")
def test_cmd_leaderboard(mock_get, capsys):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {
            "id": 1,
            "github_username": "HassanKorey",
            "merged_prs": 18,
            "points_earned": 2700,
        }
    ]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_resp

    cli = DripsLensCLI(base_url="http://test")
    parser = build_parser()
    args = parser.parse_args(["leaderboard"])
    cli.cmd_leaderboard(args)

    captured = capsys.readouterr()
    assert "HassanKorey" in captured.out
    assert "2700" in captured.out


@patch("httpx.Client.get")
def test_cmd_search(mock_get, capsys):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {
            "id": 1,
            "title": "Implement Soroban indexer",
            "complexity": "Medium",
            "points": 150,
            "is_claimed": True,
            "url": "https://github.com/...",
        },
        {
            "id": 2,
            "title": "Fix bug in redis",
            "complexity": "Trivial",
            "points": 50,
            "is_claimed": False,
            "url": "https://github.com/...",
        },
    ]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_resp

    cli = DripsLensCLI(base_url="http://test")
    parser = build_parser()
    args = parser.parse_args(["search", "soroban"])
    cli.cmd_search(args)

    captured = capsys.readouterr()
    assert "Implement Soroban indexer" in captured.out
    assert "Fix bug in redis" not in captured.out
