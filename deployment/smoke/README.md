# ArthLens Deployment Smoke Verification Suite

> **Authoritative Specification**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (Section 14.5)
> **Phase**: Phase 1 foundation (expanded in Phase 7)

## Procedure

1. Copy `deployment/env.example` to `deployment/.env`, set real database and JWT
   credentials, set the public API URL and frontend origin, and provide the
   Gemini key. Keep the file out of version control.
2. Run the offline preflight: `python -m scripts.deployment_preflight deployment/.env`.
   It validates environment shape and migration ordering without printing
   secrets or connecting to a database.
3. Start the production stack from the repository root:
   `docker compose --env-file deployment/.env -f deployment/compose.yaml up -d --build`.
   TLS termination and public DNS belong at the external reverse proxy. Compose
   binds the API and frontend to localhost by default.
4. Run the authenticated smoke checks using an existing deployment operator
   account: `python deployment/smoke/run_smoke_checks.py --base-url http://127.0.0.1:8000`.
   Set `ARTHLENS_SMOKE_EMAIL` and `ARTHLENS_SMOKE_PASSWORD`, or pass `--email`
   and `--password`. The script creates a unique workspace, checks its live
   financial snapshot and PDF report, and archives the workspace in a `finally`
   cleanup step.
5. Verify `docker compose ... ps` reports healthy database, API, and frontend
   services, and that the one-shot migration service completed successfully.

The smoke checks make authenticated API calls and create a short-lived archived
workspace. Use an operator account authorized to create and archive workspaces.
