import requests
import time

def fetch_issues_for_repo(repo_name: str, retries: int = 3):
    # Fetch issues from GitHub API with retry logic and rate limit handling
    for attempt in range(retries):
        try:
            # Placeholder for actual API call, e.g., requests.get(...)
            # if response.status_code == 403: # Rate limited
            #    time.sleep(60)
            #    continue
            return [
                {"title": "Fix bug in API", "url": f"https://github.com/{repo_name}/issues/1", "complexity": "Medium", "points": 150},
            ]
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
    return []

def fetch_contributors():
    # Fetch top contributors based on merged PRs
    # Return placeholder data for now
    return [
        {"github_username": "alice", "merged_prs": 10, "points_earned": 1500},
        {"github_username": "bob", "merged_prs": 5, "points_earned": 800},
    ]
