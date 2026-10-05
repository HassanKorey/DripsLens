from app.scrapers.stellar_verifier import verify_stellar_account
from app.scrapers.github_fetcher import fetch_issues_for_repo, fetch_contributors
from app.scrapers.drips_scraper import scrape_approved_repos

def test_verify_stellar_account():
    # Example unit test
    # This might require mocking requests in a real test
    assert verify_stellar_account("invalid_account") == False

def test_fetch_issues():
    issues = fetch_issues_for_repo("stellar/stellar-core")
    assert len(issues) > 0
    assert "title" in issues[0]

def test_fetch_contributors():
    contributors = fetch_contributors()
    assert len(contributors) > 0
    assert "github_username" in contributors[0]

def test_scrape_approved_repos():
    repos = scrape_approved_repos()
    assert len(repos) > 0
    assert "name" in repos[0]
