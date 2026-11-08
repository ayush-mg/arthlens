# Open Questions and Verification Register (Phase 0)

> **Document Status**: Active Working Document
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)
> **Rule**: Items marked with **`[VERIFY]`** must be verified against primary sources before being relied upon in code or architecture. Never invent answers. Every verification must be recorded with date, official source URL, and supporting evidence.

---

## 1. Canonical Data Source Register

This register records scope-specific investigation results, not blanket source
approval. The [Master Execution Tracker](MASTER_EXECUTION_TRACKER.md) is
authoritative for current roadmap status. Historical `PENDING` labels below
identify open questions; source decisions are limited to the explicit scopes in
each source document. No AI-generated or extracted status is a substitute for
required human sign-off.

| Source ID | Source Name | Canonical Documentation Path | Key Questions Requiring Verification | Status | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DS-01** | **data.gov.in** | [`docs/data-sources/ds-01-data-gov-in.md`](data-sources/ds-01-data-gov-in.md) | Mandi price unit, resource-specific reuse terms/attribution, nationwide gaps and freshness policy. | `PENDING` | Human source reviewer |
| **DS-02** | **RBI DBIE** | [`docs/data-sources/ds-02-rbi-dbie.md`](data-sources/ds-02-rbi-dbie.md) | Revisit official BSR tables, availability, staleness and terms only if R1 scope is activated. | `DEFERRED (R1)` | Product decision |
| **DS-03** | **SHRUG** | [`docs/data-sources/ds-03-shrug.md`](data-sources/ds-03-shrug.md) | Revisit licence, crosswalk and staleness only if a suitable use/licence path is established. | `DEFERRED / CONDITIONAL NO-GO` | Human legal review if scope changes |
| **DS-04** | **OpenStreetMap** | [`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md) | Confirm ODbL attribution/share-alike treatment and completeness limits for the accepted pilot use. | `PILOT GO; review scope-limited` | Human source/licence reviewer |
| **DS-05** | **Census 2011 / LGD crosswalk** | [`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md) | Preserve the 2011 vintage/stale flag; verify nationwide source/vintage scope and crosswalk changes before expansion. | `SCOPED GO; review scope-limited` | Human source reviewer |
| **DS-06** | **NSS / HCES** | [`docs/data-sources/ds-06-nss-consumption.md`](data-sources/ds-06-nss-consumption.md) | Reassess geographic granularity and use if R1 downscaling is pursued. | `DEFERRED (R1)` | Product decision |
| **DS-07** | **Udyam statistics** | [`docs/data-sources/ds-07-udyam.md`](data-sources/ds-07-udyam.md) | No spatial private-address ingestion; macro-count use remains separately deferred. | `NO-GO (Spatial) / DEFERRED (Macro)` | Human review if scope changes |
| **DS-08** | **Government scheme guidelines** | [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md) | Official PDFs/hashes and extracted references exist; independently verify parameters, current effective dates, mechanisms, and user-assumption handling. | `BLOCKED for operational rules (P0-2)` | Qualified human policy reviewer |
| **DS-09** | **Administrative boundaries** | [`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md) | Keep Prayagraj pilot approval scoped; obtain and verify authoritative modern nationwide/subdistrict sources before expansion. | `PILOT ONLY; nationwide gated` | Human source/licence reviewer |

---

## 2. Government Scheme Guidelines: Human Validation Gate (Task P0-2)

Official PDFs, hashes, and a machine-extracted/citation-referenced parameter
register are present in [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md)
and [`docs/schemes/parameter_register.md`](schemes/parameter_register.md).
This is source research, not independent human approval. No scheme-specific
runtime rule or financing recommendation may be treated as approved until a
qualified human confirms each parameter against the current official document,
effective date, page/section, and mechanism.

> **Current status**: `BLOCKED` pending independent human verification and approval. Do not copy parameter values from the extracted register into production policy rules.

---

## 3. Pilot District Selection (Task P0-4)

A human-approved decision record selecting **Prayagraj (Uttar Pradesh)** and two
business templates is recorded in [`docs/DECISIONS.md`](DECISIONS.md). This
historical decision does not close the current evidence gate: prerequisite
source licensing, scheme-rule approval, and complete current go/no-go
reconciliation remain open in the Master Execution Tracker. Do not treat
unverified datasets or scheme parameters as production evidence.

---

## 4. Hosting, Infrastructure, and Deployment Questions (Part 14; P0-6 BLOCKED)

Prior research and decision notes are recorded in
[`docs/hosting-and-llm-decision.md`](hosting-and-llm-decision.md) and
[`docs/DECISIONS.md#adr-009`](DECISIONS.md#adr-009-hosting-limits-deployment-architecture-and-llm-provider-selection-task-p0-6).
These notes are not current procurement evidence or authorization. P0-6 remains
blocked until current official vendor terms, pricing, quotas, deployment
support, and data-processing terms are checked and a human authorizes the
choices.

### 4.1 Local Development Boundary
- **Status**: `IMPLEMENTED LOCALLY; DOES NOT AUTHORIZE PUBLIC HOSTING`
- The repository defines a local PostGIS Compose service and a backend
  container build. These support local development and tests only; no public
  provider, budget, or deployment is approved by that setup.

---

## 5. LLM Provider, Cost Governance, and Evaluation Questions (Part 8.6, 8.3, 12.2; P0-6 BLOCKED)

### 5.1 Provider Selection and Privacy Terms
- **Status**: `UNVERIFIED / NOT AUTHORIZED`
- Earlier model names, prices, terms, and quota statements in this document
  were not sufficiently tied to a current primary-source review. They are
  withdrawn as procurement guidance. Verify current model availability,
  pricing, retention/training terms, quotas, and account-specific limits
  directly against official provider documentation before a human selects a
  provider.
- No live provider credentials or paid API usage are authorized by this
  document. The implemented interface/test-double architecture does not
  constitute a provider selection.

### 5.2 Cost Governance and Runtime Readiness
- **Configured cost controls**: `CONFIGURATION EXISTS; OPERATIONAL AGENT ENFORCEMENT NOT ACCEPTED`.
  Budget and quota settings may exist in the API/configuration, but Phase 4
  orchestration, provider adapters, and measured model costs are not accepted
  as complete. Treat amounts as unmeasured configuration, not verified safety
  margins.
- **Offline / replay modes**: `NOT VERIFIED AS END-TO-END AGENT RUNS`.
  An interface or test double is not evidence that golden workflow traces or
  an end-to-end replay engine exist. See P4-3 and P5-4.

### 5.3 Agent Evaluation Benchmark (Part 12.2)
- **Status**: `FORMAT EXISTS; GOLD LABELS OUTSTANDING`.
  A task schema and development sample exist. Independently labelled
  validation/frozen sets and benchmark results are not established; see P6-1.

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
   - *Status*: `RESEARCH DOCUMENTED; HUMAN REVIEW PENDING (P0-3 IN PROGRESS)`
   - *Evidence*: Findings and limitations are documented in [`docs/name-search.md`](name-search.md). They are not legal clearance or a guarantee of trademark/domain availability; human review is required before public or commercial claims.
   - *Blocks Implementation*: No for private development; yes for public name-availability or commercial claims.
3. **Competitor & Precedent Analysis (Section 1.5, Task P0-3)**:
   - *Status*: `RESEARCH DOCUMENTED; HUMAN REVIEW PENDING (P0-3 IN PROGRESS)`
   - *Evidence*: Findings are documented in [`docs/competitor-analysis.md`](competitor-analysis.md). Recheck primary sources and have a human review before making public comparative or market-gap claims.
   - *Blocks Implementation*: No for private development; yes for public comparative claims.
4. **Huff Model Parameter Calibration (Section 6.3)**:
   - *Status*: `OPEN (P3-2 allocator implemented; scenario calibration remains unverified)`
   - Check literature for documented empirical bounds on distance decay exponent $\lambda$ in Indian semi-urban retail contexts. The implementation requires an explicit scenario value and does not provide a default.
   - *Blocks Implementation*: No for the allocator implementation; yes for recommending a calibrated default or presenting a real-world calibrated result.

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
