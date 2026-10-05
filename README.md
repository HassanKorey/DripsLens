# DripsLens

DripsLens is a Python/FastAPI backend service that aggregates, caches, and serves data about Drips Wave approved repositories, open issues, contributor activity, and point values.

## Architecture

- **Backend**: Python, FastAPI
- **Database**: PostgreSQL
- **Caching**: Redis
- **Task Scheduling**: APScheduler
- **Frontend**: Jinja2 Templates

## Getting Started

1. Clone the repository
2. Run `docker-compose up -d` to start the database, Redis, and API server.
3. Access the API at `http://localhost:8000`

## Contributing

Please read `CONTRIBUTING.md` for details on our code of conduct, and the process for submitting pull requests to us.
