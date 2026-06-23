# Observability Runbook

## Purpose

Run Prometheus and Grafana for Telite LMS runtime visibility.

## Start Local/Staging Observability

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d prometheus grafana
```

Default ports:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`

## Metrics Source

Telite backend exposes:

```text
/metrics
```

Current metrics:

- `telite_http_requests_total`
- `telite_http_errors_total`

## Alerts

Alert rules live in:

```text
docker/observability/alert-rules.yml
```

Initial alerts:

- Backend metrics endpoint down.
- Elevated 5xx count.
- No traffic observed.

## Production Requirements

Before go-live, expand metrics to include:

- request latency histograms
- route/status counters
- database pool metrics
- Redis health metrics
- Celery worker metrics
- enrollment events
- course completion events
- quiz submissions
- assignment grading latency
- certificate issuance
- gradebook recalculation failures

## Dashboard

Starter dashboard:

```text
docker/observability/grafana/dashboards/telite-api-overview.json
```

## Operational Checks

During incident triage:

1. Check `/health/readiness`.
2. Check Prometheus `up{job="telite-backend"}`.
3. Check 5xx increase.
4. Check backend logs with request IDs.
5. Check database and Redis container health.

