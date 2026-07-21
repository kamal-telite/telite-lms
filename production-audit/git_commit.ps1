python production-audit/clean_console_logs.py
git reset HEAD
git add telite-backend
git add docker docker-compose.yml telite-frontend/Dockerfile
git rm Dockerfile
git commit -m "chore: remove legacy Moodle dependencies from backend and docker"
git add telite-frontend
git commit -m "chore: remove legacy Moodle UI components and update dependencies"
git add production-audit
git commit -m "docs: production audit reports and remediation scripts"
