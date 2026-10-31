# Open Questions and Verification Register (Phase 0)

> **Document Status**: Active Working Document
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)
> **Rule**: Items marked with **`[VERIFY]`** must be verified against primary sources before being relied upon in code or architecture. Never invent answers. Every verification must be recorded with date, official source URL, and supporting evidence.

---

## 1. Canonical Data Source Register (Pending Verification)

The following canonical identifiers and files govern all data source investigations:

| Source ID | Source Name | Canonical Documentation Path | Key Questions Requiring Verification | Status | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DS-01** | **data.gov.in** | [`docs/data-sources/ds-01-data-gov-in.md`](data-sources/ds-01-data-gov-in.md) | • Exact `resource_id` endpoints for pilot district indicators.<br>• API rate limits (requests per min/day).<br>• GODL India licence compliance and exact attribution terms.<br>• Freshness and retrieval schema. | `PENDING` | Dev A+B |
| **DS-02** | **RBI DBIE** | [`docs/data-sources/ds-02-rbi-dbie.md`](data-sources/ds-02-rbi-dbie.md) | • Exact tables providing district Scheduled Commercial Bank deposits and credit statistics (BSR returns).<br>• Download format (API vs. bulk CSV/XLSX).<br>• Staleness risk: verify whether data past 2022 is available on official DBIE.<br>• Terms of use for non-commercial research. | `PENDING` | Dev A+B |
| **DS-03** | **SHRUG** | [`docs/data-sources/ds-03-shrug.md`](data-sources/ds-03-shrug.md) | • Licence terms for non-academic/external software evaluation.<br>• Feasibility of crosswalking Census 2011 village identifiers to current LGD codes.<br>• Completeness of population and non-farm establishment counts for pilot district.<br>• Application of `STALE` quality flag (data derived from 2011 Census / 2013 Economic Census). | `PENDING` | Dev A+B |
| **DS-04** | **OpenStreetMap** | [`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md) | • Completeness of road network graph and relevant POI density in pilot district.<br>• ODbL 1.0 attribution and share-alike obligations when deriving catchment boundaries and vector tiles. | `PENDING` | Dev A+B |
| **DS-05** | **Census 2011 / LGD crosswalk** | [`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md) | • Official Local Government Directory (LGD) availability and machine-readable format.<br>• Authoritative crosswalk table linking 2011 Census village/town codes to LGD codes.<br>• Strategy for newly bifurcated districts or renamed administrative blocks. | `PENDING` | Dev A |
| **DS-06** | **NSS / HCES** | [`docs/data-sources/ds-06-nss-consumption.md`](data-sources/ds-06-nss-consumption.md) | • Which survey round (e.g. 68th round or latest HCES) is accessible in machine-readable format?<br>• Level of geographic aggregation (state vs. NSS region vs. district) and food/retail category breakdown.<br>• Empirical basis for `popweight_v1` spatial downscaling. | `PENDING` | Dev A |
| **DS-07** | **Udyam statistics** | [`docs/data-sources/ds-07-udyam.md`](data-sources/ds-07-udyam.md) | • Availability of publicly downloadable district-level MSME registration counts.<br>• Sectoral granularity (NIC codes for retail and food processing). | `PENDING` | Dev A |
| **DS-08** | **Government scheme guidelines** | [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md) | • Download official PDFs for PMFME, PMEGP, PM-MUDRA.<br>• Compute SHA-256 hashes and extract subsidy rates, caps, loan terms, and moratorium mechanisms by hand. | `PENDING` | Dev B |
| **DS-09** | **Administrative boundaries** | [`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md) | • Compliance with Survey of India digital boundary dissemination guidelines.<br>• Licence and format (GeoJSON/PMTiles) of open boundary geometries for national, state, and district levels. | `PENDING` | Dev B |

---

## 2. Government Scheme Guidelines Requiring Verification (Task P0-2)

All ground truth scheme logic must be documented in canonical [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md).

> **Crucial Rule**: The parameters below are **illustrative research leads** extracted from introductory handbook notes and secondary summaries. They are **not** confirmed rules. Every parameter must be verified by reading official primary PDFs, recording the document SHA-256 checksum, and citing specific page numbers.

### 2.1 PMFME (PM Formalisation of Micro food processing Enterprises Scheme)
- **Primary Source Portal**: Ministry of Food Processing Industries (MoFPI).
- **Leads to Investigate [ILLUSTRATIVE / UNVERIFIED LEAD]**:
  - Credit-linked capital subsidy rate: illustrative 35%, capped at ₹10 lakh.
  - Beneficiary contribution: illustrative 10% of project cost.
  - Subsidy disbursement mechanism: is it `ADJUSTS_PRINCIPAL`, `BACK_ENDED_RELEASE`, or `LOCKED_DEPOSIT` in an interest-free reserve account?
  - Moratorium terms and treatment of interest during moratorium (paid monthly vs capitalized into debt).
  - Priority criteria under One District One Product (ODOP) framework.
- **Status**: `PENDING` verification.

### 2.2 PMEGP (Prime Minister's Employment Generation Programme)
- **Primary Source Portal**: Khadi and Village Industries Commission (KVIC) / Ministry of MSME.
- **Leads to Investigate [ILLUSTRATIVE / UNVERIFIED LEAD]**:
  - Maximum project cost ceiling for manufacturing (illustrative ₹50 lakh) vs service/business units (illustrative ₹20 lakh).
  - Margin money (subsidy) percentage: variation between general category (15% urban / 25% rural) and special category (25% urban / 35% rural).
  - Own-contribution requirement (10% general, 5% special).
  - Lock-in period of subsidy before final adjustment against term loan.
- **Status**: `PENDING` verification.

### 2.3 PM-MUDRA (Pradhan Mantri MUDRA Yojana)
- **Primary Source Portal**: MUDRA official portal / Department of Financial Services.
- **Leads to Investigate [ILLUSTRATIVE / UNVERIFIED LEAD]**:
  - Loan category tier boundaries: Shishu (up to ₹50,000), Kishore (₹50,000 to ₹5 lakh), Tarun (₹5 lakh to ₹10 lakh / Tarun Plus if applicable).
  - Collateral-free provisions and Credit Guarantee Fund coverage.
  - Repayment tenures and maximum bank moratorium allowed.
  - Applicable interest rate structures (bank benchmark rates).
- **Status**: `PENDING` verification.

---

## 3. Pilot District Selection (Task P0-4)

The handbook proposes **Prayagraj (Uttar Pradesh)** as the candidate district, subject to the **Go / No-Go Gate (Handbook Section 7.3)**:
1. **Road Network & POI Density**: Check OSM road graph connectivity and count POIs by category in Prayagraj.
2. **Population Data Resolution**: Verify population data availability at sub-district or village level with a documented `as_of` date.
3. **Scheme Guideline Availability**: Confirm that official guidelines for PMFME, PMEGP, and PM-MUDRA are fetched, hashed, and readable.
4. **Business Templates**: Confirm feasibility of modeling neighbourhood retail and small food-processing / tiffin units against available local data.

*If any criterion fails*: An alternate district (e.g. Varanasi or Pune) will be evaluated or the geographic claim adjusted.

---

## 4. Hosting, Infrastructure, and Deployment Questions (Part 14)

> Detailed audit and benchmark data are recorded in [`docs/hosting-and-llm-decision.md`](hosting-and-llm-decision.md) and [`docs/DECISIONS.md#adr-009`](DECISIONS.md#adr-009-hosting-limits-deployment-architecture-and-llm-provider-selection-task-p0-6).

### 4.1 Blocking Decisions (Required for Phase 1 Implementation)
- **Local Database Environment**:
  - *Status*: `RESOLVED`
  - *Evidence*: Local development and CI are decoupled from external cloud providers. PostgreSQL 16 + PostGIS 3.4 will be provisioned locally via standard Docker Compose (`postgis/postgis:16-3.4-alpine`) and GitHub Actions service container. No cloud hosting credentials required for Phase 1.
  - *Blocks Implementation*: No.
- **Database Schema & Job Queue Validation**:
  - *Status*: `RESOLVED`
  - *Evidence*: Handbook Part 3.1 & 3.2 specifies a single PostgreSQL datastore with PostGIS, GIN indexing on `parent_ids UUID[]`, and `jobs` table polling via `SELECT ... FOR UPDATE SKIP LOCKED`. Validated against PostgreSQL 16 capabilities. Celery, Redis, and vector DBs are strictly excluded in MVP.
  - *Blocks Implementation*: No.
- **LLM Decoupling Interface (`ILLMClient`)**:
  - *Status*: `RESOLVED`
  - *Evidence*: `ILLMClient` abstract base class decouples domain logic from provider SDKs. `FakeLLMClient` (synthetic schema-valid fixtures) and `ReplayLLMClient` (stored golden runs) enable 100% offline, zero-cost unit/property test execution in Phase 1.
  - *Blocks Implementation*: No.

### 4.2 Deployment Decisions (Resolved Ahead of Phase 7 Deployment)
- **Managed Database Provider (PostgreSQL + PostGIS)**:
  - *Status*: `RESOLVED (Neon Recommended / Supabase Alternative)`
  - *Evidence*:
    - **Neon Postgres**: Free tier includes 1 GB storage, 100 CU-hours/mo, autoscales 0–2 CU. Native `CREATE EXTENSION postgis;` verified. Scales to zero after 5 min idle with ~300ms–2s cold resume. 1 GB comfortably fits Prayagraj GIS geometries (~150 MB).
    - **Supabase**: Free tier includes 500 MB database storage, native PostGIS support. Pauses after 7 days inactivity; read-only lock if >500 MB.
    - **Render Postgres Free**: `REJECTED` because free instances are permanently deleted after 30 days.
  - *Blocks Implementation*: No.
- **Backend Container & Worker Execution**:
  - *Status*: `RESOLVED (Starter $7/mo or In-Process Worker)`
  - *Evidence*:
    - Free Render Web Service sleeps after 15 min idle (30–60s cold start) and does not support free standalone background workers.
    - Hugging Face Spaces (`cpu-basic`, 16 GB RAM Docker) sleeps after 48 hours of inactivity (10–30s cold start) with ephemeral disk.
    - *Decision*: To ensure background Monte Carlo and agent jobs do not drop, the public demo will run on Render Starter ($7/mo always-on) or use an in-process async worker loop inside the web container. Replay Mode (Part 14.4) serves as the primary fallback for zero-downtime evaluation.
  - *Blocks Implementation*: No.
- **Frontend Hosting**:
  - *Status*: `RESOLVED (Cloudflare Pages Recommended / Vercel Hobby Fallback)`
  - *Evidence*:
    - **Cloudflare Pages**: Free tier includes unlimited bandwidth, 500 builds/mo, 100k Worker requests/day, and **explicitly permits commercial use**.
    - **Vercel Hobby**: Free tier includes 100 GB transfer, 300s timeout, but is **strictly restricted to non-commercial personal use**. Acceptable for university coursework/demo, but not commercial launch.
  - *Blocks Implementation*: No.
- **Object Storage for PMTiles Vector Maps & Exports**:
  - *Status*: `RESOLVED (Cloudflare R2 Recommended)`
  - *Evidence*: Cloudflare R2 provides 10 GB standard storage free per month, 1M write / 10M read operations, 100% S3 API compatibility, and **$0.00 data egress fees**. AWS S3 charges $0.09/GB egress, introducing bill shock risk on public vector tile downloads.
  - *Blocks Implementation*: No.

---

## 5. LLM Provider, Cost Governance, and Evaluation Questions (Part 8.6, 8.3, 12.2)

### 5.1 Provider Models & Privacy Terms
- **Primary LLM Provider**:
  - *Status*: `RESOLVED (OpenAI API Recommended)`
  - *Evidence*:
    - Active primary workhorse: **`gpt-6-luna`** ($0.10/1M input, $0.50/1M output, $0.01 cached input, ~1.05M context). Features native guaranteed JSON Schema enforcement (`response_format: { type: "json_schema", strict: true }`).
    - Deprecation notice: `gpt-4o-mini` and `gpt-4o` were officially deprecated on October 14, 2026, with API shutdown scheduled for January 14, 2027.
    - Active reasoning model: **`gpt-5.6-terra`** ($2.00/1M input, $12.00/1M output) for bounded replanning and policy extraction.
    - Privacy Terms: **OpenAI commercial API terms explicitly guarantee that API inputs and outputs are NOT used to train OpenAI models**. Data retained up to 30 days solely for abuse monitoring.
    - Rate Limits: `CONDITIONAL (Account Tier Dependent)`. Starting at 500 RPM / 200,000 TPM on Tier 1 up to high throughput on Tier 5.
  - *Alternative Providers*: Anthropic (`claude-3-5-haiku` / `claude-3-5-sonnet`) verified compliant (no API training). Google Gemini verified that **Free tier on AI Studio USES prompts for training**, whereas only the Paid tier exempts data from training.
  - *Blocks Implementation*: No.

### 5.2 Cost Governance & Safeguards (Part 8.3)
- **Per-Run Cost Cap (`MAX_COST_USD_PER_RUN = 0.25`)**:
  - *Status*: `RESOLVED`
  - *Evidence*: The $0.25 limit is an initial unmeasured hypothesis. At `gpt-6-luna` pricing ($0.10/$0.50 per 1M), an 8-call run costs ~$0.0040 (0.40 US cents), providing a ~62x safety margin. If cumulative run cost exceeds $0.25, `BudgetEnforcementDecorator` immediately transitions the run to `BUDGET_EXHAUSTED`, returns partial outputs, and records unresolved gaps.
  - *Blocks Implementation*: No.
- **Per-Run Hard Step and Call Limits**:
  - *Status*: `RESOLVED`
  - *Evidence*: Enforced in code: Max 25 steps per run, max 3 replans, max 30 model calls, 60s tool execution timeout, 2 transient retries.
  - *Blocks Implementation*: No.
- **Offline & Replay Modes**:
  - *Status*: `RESOLVED`
  - *Evidence*: `FakeLLMClient` generates deterministic Pydantic objects for tests. `ReplayLLMClient` serves pre-recorded golden traces for Loops A, B, and C with the `REPLAY` banner, enabling zero-cost demos and evaluation without live API keys.
  - *Blocks Implementation*: No.

### 5.3 Agent Evaluation Benchmark (Part 12.2)
- **Benchmark Task Corpus**:
  - *Status*: `RESOLVED (Task P0-5 completed)`
  - *Evidence*: Benchmark task format and test suite authored and committed in P0-5. Targets 60–100 gold tasks split into dev, validation, and frozen test sets.
  - *Blocks Implementation*: No.

---

## 6. Development Environment & Python Compatibility (Resolved)

- **Status**: `RESOLVED (P1-1 Architecture Decision)`
- **Observation**: The development machine runs **Python 3.14.5**, whereas the initial handbook reference designated Python 3.12.
- **Verification**: All core backend dependencies (`fastapi`, `pydantic`, `sqlalchemy`, `alembic`, `psycopg-binary`, `numpy`, `scipy`, `pandas`, `geopandas`, `shapely`, `pyproj`, `pint`, `networkx`, `httpx`, `uvicorn`) were verified to have pre-compiled binary wheels available for Python 3.14 (`cp314-win_amd64` / `none-any`).
- **Resolution**: The project has officially standardized on **Python 3.14** across `.python-version`, `.github/workflows/ci.yml`, `deployment/Dockerfile`, and `backend/pyproject.toml`.

---

## 7. Other Unresolved Questions from the Handbook

1. **Epistemic Ledger Novelty Literature Review (Section 1.4)**:
   - *Status*: `OPEN (Academic Context)`
   - Perform a focused academic literature review comparing provenance graphs (W3C PROV, data lineage) with runtime evidence-gated agent decision systems.
   - *Rule*: Do not claim the concept is novel in any presentation or paper without prior verification.
   - *Blocks Implementation*: No.
2. **Name Availability Check**:
   - *Status*: `RESOLVED (Task P0-3 completed)`
   - *Evidence*: Documented in [`docs/name-search.md`](name-search.md). PyPI, npm, GitHub clear for coursework repo. Commercial entity `Arthlens Technologies Pvt. Ltd.` discovered in Bengaluru; commercial incorporation blocked/rebranding required before commercial startup, but academic evaluation is permissible.
   - *Blocks Implementation*: No.
3. **Competitor & Precedent Analysis (Section 1.5, Task P0-3)**:
   - *Status*: `RESOLVED (Task P0-3 completed)`
   - *Evidence*: Documented in [`docs/competitor-analysis.md`](competitor-analysis.md). Empirical functional boundaries and matrices established for ONDC, Udyam, MSME Sampark, and deep-research agents.
   - *Blocks Implementation*: No.
4. **Huff Model Parameter Calibration (Section 6.3)**:
   - *Status*: `OPEN (Scheduled for Phase 2 Demand Engine)`
   - Check literature for documented empirical bounds on distance decay exponent $\lambda$ in Indian semi-urban retail contexts.
   - *Blocks Implementation*: No (required for Phase 2, not Phase 1).

---

## 8. Rate Limiting, Quotas, and Cost-Cap Thresholds (Task P1-6) [VERIFY]

The following thresholds were audited against Handbook Part 8.3, Part 11, Part 14.3, and Appendix A:

1. **Per-Run Cost Cap (`MAX_COST_USD_PER_RUN = 0.25`)**:
   - *Status*: `VERIFIED (Initial Starting Baseline per Handbook Part 8.3)`
   - *Evidence*: Handbook Part 8.3 (Page 22) specifies: `MAX_COST_USD_PER_RUN env, start at 0.25. Behaviour at limit: BUDGET_EXHAUSTED. Measure real cost in Phase 6`. This value is an authoritative initial baseline, to be recalibrated with empirical token measurements in Phase 6.

2. **Per-IP Rate Limit (`RATE_LIMIT_PER_MINUTE_IP = 60`)**:
   - *Status*: `PROVISIONAL [VERIFY]`
   - *Evidence*: Handbook Part 11 specifies *"Per-IP and per-user limits"* but does not define a numerical threshold. 60 requests/minute is an unverified provisional heuristic. Production tuning requires empirical traffic analysis and Cloudflare/reverse proxy calibration.

3. **Per-User Rate Limit (`RATE_LIMIT_PER_MINUTE_USER = 120`)**:
   - *Status*: `PROVISIONAL [VERIFY]`
   - *Evidence*: Handbook Part 11 requires per-user throttling. 120 requests/minute is an unverified provisional default.

4. **Daily Run Quota (`DAILY_RUN_QUOTA = 50`)**:
   - *Status*: `PROVISIONAL [VERIFY]`
   - *Evidence*: Handbook Part 8.3 specifies *"Configurable quota"* and Part 11 specifies *"daily run quota"*. 50 runs/day is an unverified provisional default.

5. **Daily Accumulated Cost Cap (`MAX_COST_USD_PER_DAY = 5.00`)**:
   - *Status*: `PROVISIONAL [VERIFY]`
   - *Evidence*: Handbook Part 11 specifies *"cost cap per run and per day"* and Part 14.3 specifies *"Set a hard daily and monthly cap in the budget governor"*. $5.00/day is an unverified provisional ceiling for demo and development accounts.
