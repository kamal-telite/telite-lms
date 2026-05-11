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
