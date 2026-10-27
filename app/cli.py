"""DripsLens standalone terminal CLI client (dripslens-cli).

Enables developers to search bounties, inspect repository health signals,
view issues, and check real-time ecosystem leaderboard standings directly from the shell.
"""

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_BASE_URL = os.getenv("DRIPSLENS_API_URL", "http://localhost:8000")


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format and align tabular terminal data."""
    if not rows:
        return "No records found."

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "  ".join("-" * col_widths[i] for i in range(len(headers)))
    data_lines = [
        "  ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, sep_line] + data_lines)


class DripsLensCLI:
    """CLI client interface communicating with DripsLens REST API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            print(f"Error: Unable to connect to DripsLens API at {self.base_url}", file=sys.stderr)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)

    def cmd_repos(self, args: argparse.Namespace) -> None:
        params: dict[str, Any] = {"skip": args.skip, "limit": args.limit}
        if args.language:
            params["language"] = args.language
        if args.multiplier is not None:
            params["multiplier"] = args.multiplier

        data = self.get("/repos", params=params)
        if args.json:
            print(json.dumps(data, indent=2))
            return

        headers = ["ID", "Repository", "Language", "Multiplier", "Issues", "Health", "Verified"]
        rows = [
            [
                str(r.get("id")),
                str(r.get("name")),
                str(r.get("language") or "-"),
                str(r.get("multiplier")),
                str(r.get("issue_count")),
                f"{r.get('health_score')}%",
                "Yes" if r.get("is_verified") else "No",
            ]
            for r in data
        ]
        print(format_table(headers, rows))

    def cmd_issues(self, args: argparse.Namespace) -> None:
        params: dict[str, Any] = {"skip": args.skip, "limit": args.limit}
        if args.complexity:
            params["complexity"] = args.complexity
        if args.is_claimed is not None:
            params["is_claimed"] = str(args.is_claimed).lower()

        data = self.get("/issues", params=params)
        if args.json:
            print(json.dumps(data, indent=2))
            return

        headers = ["ID", "Title", "Complexity", "Points", "Claimed", "URL"]
        rows = [
            [
                str(i.get("id")),
                str(i.get("title"))[:45],
                str(i.get("complexity")),
                str(i.get("points")),
                "Claimed" if i.get("is_claimed") else "Open",
                str(i.get("url")),
            ]
            for i in data
        ]
        print(format_table(headers, rows))

    def cmd_leaderboard(self, args: argparse.Namespace) -> None:
        params = {"limit": args.limit}
        data = self.get("/leaderboard", params=params)
        if args.json:
            print(json.dumps(data, indent=2))
            return

        headers = ["Rank", "Contributor", "Merged PRs", "Points Earned"]
        rows = [
            [
                str(rank),
                str(c.get("github_username")),
                str(c.get("merged_prs")),
                str(c.get("points_earned")),
            ]
            for rank, c in enumerate(data, start=1)
        ]
        print(format_table(headers, rows))

    def cmd_search(self, args: argparse.Namespace) -> None:
        query = args.query.lower()
        all_issues = self.get("/issues", params={"limit": 100})
        matched = [
            i for i in all_issues
            if query in i.get("title", "").lower()
            or query in i.get("complexity", "").lower()
            or query in i.get("url", "").lower()
        ]
        if args.json:
            print(json.dumps(matched, indent=2))
            return

        print(f"Search results for '{args.query}' ({len(matched)} match(es)):")
        headers = ["ID", "Title", "Complexity", "Points", "Claimed", "URL"]
        rows = [
            [
                str(i.get("id")),
                str(i.get("title"))[:45],
                str(i.get("complexity")),
                str(i.get("points")),
                "Claimed" if i.get("is_claimed") else "Open",
                str(i.get("url")),
            ]
            for i in matched
        ]
        print(format_table(headers, rows))


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dripslens",
        description="DripsLens CLI - Terminal Search & Ecosystem Analytics Client",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_BASE_URL,
        help="DripsLens API server base URL (default: http://localhost:8000 or $DRIPSLENS_API_URL)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # repos subcommand
    parser_repos = subparsers.add_parser("repos", help="List tracked Wave repositories")
    parser_repos.add_argument("--language", help="Filter repositories by programming language")
    parser_repos.add_argument("--multiplier", type=int, help="Filter by point multiplier")
    parser_repos.add_argument("--skip", type=int, default=0, help="Pagination offset")
    parser_repos.add_argument("--limit", type=int, default=20, help="Pagination limit")
    parser_repos.add_argument("--json", action="store_true", help="Output raw JSON")

    # issues subcommand
    parser_issues = subparsers.add_parser("issues", help="List ecosystem bounty issues")
    parser_issues.add_argument("--complexity", choices=["Trivial", "Medium", "High"], help="Filter by complexity tier")
    parser_issues.add_argument("--claimed", dest="is_claimed", action="store_true", default=None, help="Show claimed issues")
    parser_issues.add_argument("--unclaimed", dest="is_claimed", action="store_false", help="Show unclaimed issues")
    parser_issues.add_argument("--skip", type=int, default=0, help="Pagination offset")
    parser_issues.add_argument("--limit", type=int, default=20, help="Pagination limit")
    parser_issues.add_argument("--json", action="store_true", help="Output raw JSON")

    # leaderboard subcommand
    parser_leaderboard = subparsers.add_parser("leaderboard", help="Display top ecosystem contributors")
    parser_leaderboard.add_argument("--limit", type=int, default=10, help="Number of contributors to show (1-100)")
    parser_leaderboard.add_argument("--json", action="store_true", help="Output raw JSON")

    # search subcommand
    parser_search = subparsers.add_parser("search", help="Search bounty issues by keyword")
    parser_search.add_argument("query", help="Keyword to search in issue titles and URLs")
    parser_search.add_argument("--json", action="store_true", help="Output raw JSON")

    return parser


def main() -> None:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args()

    cli = DripsLensCLI(base_url=args.api_url)

    if args.command == "repos":
        cli.cmd_repos(args)
    elif args.command == "issues":
        cli.cmd_issues(args)
    elif args.command == "leaderboard":
        cli.cmd_leaderboard(args)
    elif args.command == "search":
        cli.cmd_search(args)


if __name__ == "__main__":
    main()
