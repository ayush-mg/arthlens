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

To prevent premature optimization, hosting and infrastructure questions are separated into **blocking decisions** (required for Phase 1 development) and **deployment decisions** (resolved before Phase 7 deployment):

### 4.1 Blocking Decisions (Required for Phase 1)
- **Local Database Environment**:
  - Verify that a standard Docker Compose service running PostgreSQL 16 + PostGIS 3.4 works smoothly in local development and GitHub Actions CI.
- **Database Schema Validation**:
  - Confirm table schemas, GIN indexing on `parent_ids UUID[]`, and `jobs` table `FOR UPDATE SKIP LOCKED` behavior.

### 4.2 Deployment Decisions (Can Legitimise Wait Until Phase 7)
- **Managed Database Provider**:
  - Confirm PostGIS extension availability on free/starter tiers of Supabase, Neon, or Render.
  - Evaluate cold-start latency and scale-to-zero behavior (e.g., Neon compute pause) versus always-on starter instance ($7/month on Render).
- **Backend Container & Worker Execution**:
  - Verify whether the background worker can run as a background task within the same container as FastAPI on Render/Hugging Face Spaces or requires a separate paid worker instance.
- **Frontend Hosting & Object Storage**:
  - Verify Vercel Hobby terms for educational/portfolio major project use.
  - Confirm Cloudflare R2 bucket setup (zero egress pricing) for serving static PMTiles vector map archives.

---

## 5. LLM Provider, Cost Governance, and Evaluation Questions (Part 8.6, 8.3, 12.2)

1. **Provider Models & Interfaces**:
   - Confirm which active provider models are suitable for:
     - Structured JSON generation (goal interpretation, plan proposal).
     - Reasoning / replanning.
     - Narrative synthesis with placeholder retention (`{{q:UUID}}`).
   - Provider terms, model names, and rate limits must be configured via environment variables, not hard-coded.
2. **Cost Governance (Part 8.3)**:
   - The figure `MAX_COST_USD_PER_RUN = 0.25` is a **configurable, unmeasured starting hypothesis** from handbook Part 8.3.
   - It will be enforced in code via `BudgetEnforcementDecorator` to prevent runaway spending, and calibrated using empirical measurements during Phase 6.
3. **Agent Evaluation Benchmark (Part 12.2)**:
   - The target benchmark comprises roughly **60–100 tasks** across Loops A, B, and C with gold labels, divided into development, validation, and frozen test sets.

---

## 6. Development Environment & Python Compatibility (Unresolved)

- **Observation**: The current development machine reports **Python 3.14.5**, whereas the handbook specification (Part 3.2) designates **Python 3.12**.
- **Compatibility Risk**: Core geospatial and scientific libraries—specifically `GeoPandas`, `Shapely` (GEOS C-library bindings), `GDAL`, `NumPy`, `SciPy`, and `psycopg`—frequently lack pre-compiled binary wheels or stable compatibility on cutting-edge Python versions (such as 3.14).
- **Required Action**:
  1. We must verify wheel availability and compile/install compatibility for the required dependency stack under Python 3.14.5.
  2. If binary wheel issues or library incompatibilities occur, we must install and pin **Python 3.12** in the local environment and Docker containers as specified by the handbook.
  3. Do not silently modify the handbook's technology specification.

---

## 7. Other Unresolved Questions from the Handbook

1. **Epistemic Ledger Novelty Literature Review (Section 1.4)**:
   - Perform a focused academic literature review comparing provenance graphs (W3C PROV, data lineage) with runtime evidence-gated agent decision systems.
   - *Rule*: Do not claim the concept is novel in any presentation or paper without prior verification.
2. **Name Availability Check**:
   - Check trademark databases and software registries (PyPI, npm, GitHub) for the name "ArthLens".
3. **Competitor & Precedent Analysis (Section 1.5, Task P0-3)**:
   - Systematically inspect ONDC, Udyam, MSME Sampark, and general deep-research agents to establish exact empirical baselines.
4. **Huff Model Parameter Calibration (Section 6.3)**:
   - Check literature for documented empirical bounds on distance decay exponent $\lambda$ in Indian semi-urban retail contexts.
