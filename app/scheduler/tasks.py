from apscheduler.schedulers.background import BackgroundScheduler
from app.scrapers.drips_scraper import scrape_approved_repos
from app.scrapers.github_fetcher import fetch_issues_for_repo, fetch_contributors
from app.db.database import SessionLocal
from app.models.repo import Repo

def refresh_data():
    print("Refreshing data from GitHub and Drips...")
    # Add actual logic to save to database here
    pass

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Runs every 6 hours
    scheduler.add_job(refresh_data, 'interval', hours=6)
    scheduler.start()
