# ArthLens Deployment Smoke Verification Suite

> **Authoritative Specification**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (Section 14.5)
> **Phase**: Phase 1 foundation (expanded in Phase 7)

## Procedure
0. Run the offline production preflight before starting deployment:
   `python -m scripts.deployment_preflight deployment/env.production`.
   It validates required environment shape and the Alembic migration graph,
   never prints secret values, and does not connect to a database. A passing
   preflight is not a deployment or production-acceptance sign-off.
1. Verify container boot and PostgreSQL + PostGIS health (`pg_isready`).
2. Verify Alembic database migrations.
3. Verify public API health endpoint (`GET /api/v1/health`).
4. Execute Playwright smoke suite against frontend deployment URL.
