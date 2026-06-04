## Architecture Workspace

Two boards are rendered side by side on this canvas:

### ← Left: System Architecture Board
Shows the **current state** of the TELITE LMS infrastructure:
- Active local setup (FastAPI + SQLite)
- Docker compose stack topology
- All 3 environment variable sources (root `.env`, `telite-backend/.env`, `docker-config.php`)
- Database connection paths with active/problem indicators
- **4 confusion points** highlighted in red
- Status notes on what works and what doesn't

### → Right: Setup Comparison & Evolution
Three-column comparison of:
1. 🔴 **Current mixed setup** — conflicting env, Docker backend shares Moodle DB
2. 🟡 **Temporary SQLite** — current working state, backend decoupled from Postgres
3. 🟢 **Final hybrid PostgreSQL** — target architecture with 2 DBs + 2 users

Includes dependency flow diagrams showing how the system evolves step by step.

---

### Remaining Work (Infrastructure Only)
- [ ] Create `init.sql` for `/docker-entrypoint-initdb.d/`
- [ ] Rewire `docker-compose.yml` backend service
- [ ] Update `.env.example` with clean credential groups
- [ ] Update README with hybrid architecture docs
- [ ] Test Docker stack with full isolation

> **No backend code changes needed** — `store.py` DSN resolution already supports full separation.