# Security Remediation Notes

The security workflow is intentionally strict. It is expected to fail until the items below are remediated.

## Historical Secrets

Local Gitleaks scan found private-key material in historical `moodle.sql` commits:

- Commit `38881f0e47e7f24d0dc72818d82f10c0675e2108`
- File `moodle.sql`
- Rule `private-key`
- Lines reported by scanner: `30291`, `30333`

Local TruffleHog scan found historical Moodle archive LDAP findings:

- Commit `1ed3453945e5987da900eff28c91c51fd294dc94`
- File `moodledata.tar.gz`
- Detector `LDAP`

Required remediation:

1. Rotate any Moodle/LTI/LDAP material that may have been exposed.
2. Remove database dumps and Moodle data archives from Git history with a history rewrite tool such as `git filter-repo` or BFG.
3. Force-push only after coordinating with all contributors.
4. Re-run Gitleaks and TruffleHog before enabling the secret workflow as a required branch protection check.

## Python Dependencies

Local `pip-audit` and Safety scans currently fail on backend pins:

- `python-dotenv==1.0.1`
- `python-multipart==0.0.22`
- `PyJWT==2.8.0`
- Transitive `starlette==0.37.2` through FastAPI

Recommended first pass:

- Upgrade `python-dotenv` to at least `1.2.2`.
- Upgrade `python-multipart` to at least `0.0.27`.
- Upgrade `PyJWT` to at least `2.13.0`.
- Evaluate FastAPI/Starlette compatibility before upgrading Starlette directly.

## Frontend Dependencies

Local `npm audit --audit-level=critical` passes. High/moderate findings remain for:

- `axios`
- `react-router-dom`
- Vite/esbuild chain

Handle these in a dedicated dependency upgrade PR with frontend regression testing.
