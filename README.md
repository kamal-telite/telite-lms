# Telite LMS

Telite LMS is a multi-tenant learning management platform for companies and colleges. The repository contains a React frontend, a FastAPI backend, and a Dockerized Moodle/PostgreSQL integration layer.

## Features

- Multi-tenant company and college workspaces
- Platform-level super admin administration
- Company category administration for ATS, DevOps, Cloud, HR, and future tracks
- College-oriented student, faculty, and admin role support
- Learner dashboards, course launch flows, PAL tracking, tasks, approvals, and reporting
- Moodle integration with mock mode for local development
- Docker Compose stack for frontend, backend, Moodle, and PostgreSQL

## Architecture

```text
LMS Super Admin
|-- Companies
|   |-- ATS
|   |-- DevOps
|   |-- Cloud
|   `-- HR
`-- Colleges
    |-- Students
    |-- Faculty
    `-- Admins
```

```text
frontend (React/Vite) -> backend (FastAPI) -> PostgreSQL
                                      |
                                      `-> Moodle REST API
```

## Tech Stack

- Frontend: React 18, Vite, Zustand, Axios, Chart.js, Tailwind/PostCSS
- Backend: FastAPI, Pydantic, SQLite/PostgreSQL support
- LMS integration: Moodle REST APIs
- Infrastructure: Docker, Docker Compose, PostgreSQL 14, Nginx

## Folder Structure

```text
telite-lms/
|-- telite-frontend/
|   |-- src/
|   |   |-- assets/
|   |   |-- components/
|   |   |-- context/
|   |   |-- hooks/
|   |   |-- layouts/
|   |   |-- pages/
|   |   |-- routes/
|   |   |-- services/
|   |   |-- store/
|   |   |-- styles/
|   |   `-- utils/
|   |-- Dockerfile
|   `-- nginx.conf
|-- telite-backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- data/
|   |   |-- integrations/
|   |   `-- services/
|   |-- scripts/
|   |-- tests/
|   `-- Dockerfile
|-- moodle/
|-- scripts/
|-- docker-compose.yml
|-- Dockerfile
|-- docker-config.php
|-- .env.example
|-- .gitignore
`-- LICENSE
```

## Installation

```bash
git clone https://github.com/<owner>/telite-lms.git
cd telite-lms
cp .env.example .env
```

Frontend local run:

```bash
cd telite-frontend
npm install
npm run dev
```

Backend local run:

```bash
cd telite-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Windows helper:

```powershell
.\scripts\start-dev.ps1
```

The signup page loads roles and organizations through the Vite proxy, so the backend must be running on `127.0.0.1:8001` while the frontend runs on `localhost:3000`.

## Environment Setup

Use `.env.example` as the template. Never commit `.env`, local databases, logs, virtual environments, build output, or `node_modules`.

Important variables:

- `TELITE_DB_BACKEND`: `sqlite` for local file DB or `postgres` for Docker/PostgreSQL
- `TELITE_DATABASE_URL`: optional full PostgreSQL connection URL
- `MOODLE_MODE`: `mock` for local development, live mode when real Moodle credentials are configured
- `BACKEND_PORT`, `FRONTEND_PORT`, `MOODLE_PORT`, `POSTGRES_PORT`: local service ports

## Database Architecture

Telite LMS uses one PostgreSQL server with two logically isolated databases in Docker and PostgreSQL-backed environments:

| Database | Owner | Used By |
| --- | --- | --- |
| `moodle` | `moodleuser` | Moodle PHP application |
| `telite_backend` | `telite_backend_user` | FastAPI backend |

Critical rules:

- `MOODLE_DB_*` settings are for Moodle only.
- `TELITE_POSTGRES_*` settings are for the backend only.
- `POSTGRES_*` settings are only for PostgreSQL container bootstrap/admin access.
- Local backend development can stay on SQLite by setting `TELITE_DB_BACKEND=sqlite`.

The Docker bootstrap script under [docker/init/01-create-databases.sh](/abs/path/c:/Users/kamal/OneDrive/Desktop/telite-lms/docker/init/01-create-databases.sh) creates both logical databases on first initialization. If your Postgres volume already exists, create the second database and user manually or recreate the volume before relying on the script.

### Fresh Volume Bootstrap

Use this when you want the target production layout from scratch:

```bash
docker compose down -v
docker compose up --build
```

That path uses:

- `POSTGRES_*` for PostgreSQL bootstrap/admin access
- `MOODLE_DB_*` for Moodle only
- `TELITE_POSTGRES_*` for the FastAPI backend only

### Existing Volume Repair

If Docker is still running the old containers like `moodle_db_final` and `moodle_app_final`, the init script will not re-run because the Postgres cluster already exists.

Inspect the live cluster:

```powershell
docker exec moodle_db_final psql -U moodleuser -d postgres -c "\l"
docker exec moodle_db_final psql -U moodleuser -d postgres -c "\du"
```

Repair the existing cluster in place with the repo script:

```powershell
.\scripts\provision-existing-postgres.ps1
```

That script:

- creates the missing `postgres` admin role if the old cluster does not have one
- creates `telite_backend_user` if needed
- creates `telite_backend` if needed
- reapplies ownership and grants for `moodle`, `telite_backend`, and `postgres`

The SQL it runs lives in [docker/sql/provision-existing-postgres.sql](/abs/path/c:/Users/kamal/OneDrive/Desktop/telite-lms/docker/sql/provision-existing-postgres.sql).

### Backend Data Migration

If your local FastAPI backend has real data in SQLite that you want to preserve, switch the backend to PostgreSQL config and then run:

```powershell
cd telite-backend
python scripts/migrate_backend_to_postgres.py
```

That copies the SQLite records into `telite_backend`. If you do not need old local data, the backend will auto-create and seed its PostgreSQL schema on first startup.

## Docker Setup

```bash
cp .env.example .env
docker compose up --build
```

Default URLs:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8001/docs`
- Moodle: `http://localhost:8082`
- PostgreSQL host port: `55432`

## Moodle Integration

Moodle is kept as a separate integration boundary. The backend reads Moodle settings from environment variables and can run in `MOODLE_MODE=mock` for development. The Docker Moodle image uses `docker-config.php` as the env-driven config template; `moodle/config.php` is intentionally ignored.

## User Roles

```text
LMS_SUPER_ADMIN
|-- COMPANY_SUPER_ADMIN
|   |-- CATEGORY_ADMIN
|   |-- TRAINER
|   `-- LEARNER
`-- COLLEGE_SUPER_ADMIN
    |-- FACULTY
    |-- STUDENT
    `-- COLLEGE_ADMIN
```

## Screenshots

Add production screenshots here before publishing a public portfolio or client-facing repository.

## API Documentation

Run the backend and open:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- Health check: `http://localhost:8001/health`

## Deployment

Recommended deployment split:

- Frontend: static build served by Nginx, Vercel, Netlify, or a CDN
- Backend: FastAPI service behind HTTPS
- Database: managed PostgreSQL
- Moodle: dedicated Moodle service or managed Moodle hosting
- Secrets: environment variables or a secret manager, never Git

## Contributors

- Telite Systems

## License

This repository is licensed under MIT. Moodle itself is GPL-licensed; keep Moodle licensing obligations in mind when distributing Moodle-derived artifacts.
