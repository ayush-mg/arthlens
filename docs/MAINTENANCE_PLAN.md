# ArthLens Maintenance & Operations Plan

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Operational Tier:** High Availability & Continuous Compliance  
**Target Environment:** Local Docker Compose / Managed Cloud Linux Container

---

## 1. Routine Maintenance Protocols

### 1.1 Database Operations & Backup Strategy
- **Daily Automated Snapshots**: Execute full PostgreSQL database dumps (`pg_dump -Fc arthlens > backup_$(date +%F).dump`).
- **Transaction Log Archiving**: Enable WAL archiving for Point-in-Time Recovery (PITR).
- **Index Maintenance**: Weekly `REINDEX TABLE CONCURRENTLY` on high-growth tables (`payments`, `inventory_movements`, `agent_turns`).
- **Vacuuming**: Configure PostgreSQL autovacuum with aggressive scale factors on transactional tables (`autovacuum_vacuum_scale_factor = 0.05`).

### 1.2 Security & Credential Hygiene
- **Secret Scanning**: Pre-commit hooks and automated CI scanners to detect API keys, tokens, and private credentials.
- **Dependency Vulnerability Scanning**: Monthly `pip-audit` for backend requirements and `npm audit` for frontend packages.
- **Session Pruning**: Scheduled cron job executing `PostgresRateLimiter.prune_expired_entries()` and token blacklist cleanup.

---

## 2. Release & Deployment Protocols

### 2.1 Preflight Verification Checklist
Prior to deploying any new version or migration:
1. Run master verification script: `powershell -File scripts\verify_all.ps1`.
2. Confirm Alembic migration heads: `alembic heads` must return exactly one clean head.
3. Verify Next.js 14 production build succeeds with exit code 0 (`npm --prefix frontend run build`).
4. Ensure zero Git untracked credential artifacts exist in the repository.

### 2.2 Blue/Green Deployment Workflow
1. Deploy new container version alongside existing production pod.
2. Run automated health checks against `/api/v1/health` and `/auth/ping`.
3. Apply pending Alembic database migrations in an isolated migration job.
4. Shift incoming traffic via reverse proxy (Nginx or Traefik) to the green deployment.
5. Monitor error rates, response latencies, and transaction logs for 15 minutes before terminating the blue deployment.
