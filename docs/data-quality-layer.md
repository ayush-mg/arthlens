# ArthLens Data-Quality Layer and Staleness Flags Specification (P2-3)

> **Authoritative References**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 4.4, 4.7, Part 7.1, 7.4, 7.5 Step 10, Part 10.2, Part 13.1 P2-3).
> **Phase**: Phase 2 (P2-3 — Data-Quality Layer and Staleness Flags).
> **Acceptance Criterion**: **Atlas shades quality states correctly.**

---

## 1. Quality Vocabulary & Semantics

The data-quality layer implements the five authoritative vocabulary states defined in Handbook Part 7.5 Step 10:

| Quality State | Domain Meaning | Epistemic Basis | Atlas Hex | CSS Token | Stroke Style | Fill Opacity |
|:---|:---|:---|:---:|:---|:---:|:---:|
| **`CURRENT`** | Fresh, complete, empirical observation within max age threshold | `Kind.OBSERVED`, $\Delta t \le \text{max\_age}$ | `#22C55E` | `atlas-quality-current` | `solid` | 0.65 |
| **`INCOMPLETE`** | Attributes present but missing geographic sub-units or partial dimensions | Partial coverage or unresolved sub-tehsils | `#EAB308` | `atlas-quality-incomplete` | `dashed` | 0.60 |
| **`STALE`** | Authentic empirical observation whose observation age exceeds source threshold | `Kind.OBSERVED`, $\Delta t > \text{max\_age}$ | `#F97316` | `atlas-quality-stale` | `hatched` | 0.70 |
| **`ESTIMATED`** | Modelled, synthetic, or downscaled value rather than empirical observation | `Kind.ESTIMATED` or `SYNTHETIC_DATA` | `#3B82F6` | `atlas-quality-estimated` | `dotted` | 0.60 |
| **`UNAVAILABLE`** | Missing data; no empirical or modelled record exists for unit | Null/missing record; **never numeric 0** | `#94A3B8` | `atlas-quality-unavailable` | `diagonal-cross` | 0.45 |

---

## 2. Deterministic Precedence for Primary Display State

When an indicator or geographic unit has multiple simultaneous quality findings, the primary presentation state is selected by strict deterministic precedence:

$$\mathbf{UNAVAILABLE} > \mathbf{INCOMPLETE} > \mathbf{STALE} > \mathbf{ESTIMATED} > \mathbf{CURRENT}$$

### Preservation Invariant
Selecting a primary display state **never discards secondary quality findings**. All applicable issues, dimensions, and explanations are preserved in the `issues` list of `IndicatorQualityAssessment` for inspection in the Atlas Provenance drawer.

---

## 3. Date Separation & Staleness Evaluation

Staleness evaluation strictly separates five distinct dates:

1. **Observation Date (`as_of`)**: The temporal ground-truth period when the physical measurement occurred (e.g. `2011-03-01` for Census 2011).
2. **Publication Date**: When the government agency or publisher released the dataset snapshot (e.g. `2013-04-30`).
3. **Retrieval Date**: When ArthLens fetched or downloaded the file (e.g. `2026-11-06`).
4. **Ingestion Date**: When ArthLens loaded the normalized records into PostgreSQL.
5. **Evaluation Date**: The clock time when freshness is assessed (supports injected test clocks).

### Critical Staleness Invariants
- **Non-Conflation of Retrieval and Observation**: Downloading Census 2011 files in November 2026 does **NOT** make historical observations fresh or current. Freshness is measured strictly as $\Delta t = \text{evaluation\_date} - \text{as\_of}$.
- **Census 2011 Ten-Year Rule & Boundary Date Arithmetic**:
  - `as_of = "2011-03-01"`, `max_age_days = 3650` (10 years).
  - Due to leap years in 2012, 2016, and 2020 (3 leap years in the ten-year period):
    - Exactly 3,650 elapsed days lands on **2021-02-26** (`2011-03-01 + 3650 days = 2021-02-26`). Evaluated on 2021-02-26, $\Delta t = 3650 \le 3650 \implies$ **NOT stale** (freshness boundary edge).
    - 3,651 elapsed days lands on **2021-02-27** (`2011-03-01 + 3651 days = 2021-02-27`). Evaluated on 2021-02-27, $\Delta t = 3651 > 3650 \implies$ **strictly `STALE`**.
    - Evaluated on 6 November 2026: $\Delta t = 5,729\text{ days} > 3,650\text{ days} \implies$ **strictly `STALE`**.
  - `Kind.OBSERVED` is strictly preserved (it represents authentic government enumerations, not synthetic estimates).
  - It must **never** be represented as current population.
- **Separation of Census Observations vs. Administrative Crosswalk Records**:
  - Census 2011 Primary Census Abstract (PCA) observations (`DS-05` / `DS-05-PCA`) represent demographic counts from the 2011 enumeration (`as_of = 2011-03-01`) and are subject to the 10-year freshness rule.
  - LGD administrative crosswalk directory records (`DS-05-LGD`) represent statutory administrative mappings (LGD codes for States, Districts, Tehsils) maintained by MoPR for the 2024–2026 directory structure. Their temporal meaning is statutory directory currency, distinct from 2011 census demographic observations.
- **Unconfigured Freshness Policies & Guard against Erroneous CURRENT Labeling**:
  - For sources lacking an approved policy, ArthLens does **NOT** invent arbitrary thresholds.
  - Freshness is explicitly marked `has_policy=False` and reported as unverified.
  - The evaluator **never labels evidence `CURRENT` solely because no threshold exists**. Empirical observations from unconfigured sources are classified as `INCOMPLETE` with an unverified freshness warning.

### Freshness Policy Approval Audit & Register

| Source ID | Source Name | Documented Policy Status | Threshold | Justification / Approval Citation |
|:---|:---|:---:|:---:|:---|
| **`DS-05`** (PCA) | Census 2011 Demographic Counts | **APPROVED** | **3,650 days** (10 years) | Handbook Part 7.4 ("The 10-year rule: Census 2011 data cannot support claims about 2026 conditions without qualification") & `docs/data-sources/ds-05-lgd-crosswalk.md` |
| **`DS-05`** (LGD) | MoPR LGD Administrative Crosswalk | **Statutory Directory** | Separate from Census | Statutory directory structure (2024–2026 baseline); distinct from historical demographic observations |
| **`DS-04`** | OpenStreetMap Road Network & POIs | **UNAPPROVED (180d)** | Unconfigured | 180 days lacks source approval. `docs/data-sources/ds-04-osm.md` (line 42) documents 30-day freshness for bulk downloads and 90-day for static fixtures. Marked `has_policy=False` in default registry. |
| **`DS-08`** | Central Government Schemes | **UNAPPROVED (365d)** | Unconfigured | 365 days lacks source approval. `docs/data-sources/ds-08-schemes.md` has no `max_age_days` (schemes follow gazetted policy cycles). Marked `has_policy=False` in default registry. |
| **`DS-09`** | Administrative Boundaries | **UNAPPROVED (1825d)** | Unconfigured | 1,825 days lacks source approval. `docs/data-sources/ds-09-administrative-boundaries.md` has no `max_age_days`. Marked `has_policy=False` in default registry. |

---

## 4. Epistemic Ledger Propagation & Calculation Gating

The quality layer integrates with the Epistemic Ledger (`backend/arthlens/ledger/`) through `CalculationQualityGate`:

1. **Missingness Gate**: If any required parent input is `UNAVAILABLE` or `None`, calculations strictly fail closed with `GatedCalculationError`. ArthLens **never silently substitutes numeric zero**.
2. **Staleness Restriction**: If any contributing parent quantity is `STALE` (or has `STALE_ANCESTRY`):
   - Derived quantities inherit the `STALE_ANCESTRY` quality flag.
   - Suitability becomes `CalculationSuitability.SUITABLE_HISTORICAL_ONLY`.
   - The result cannot silently support claims about current economic conditions.
3. **Estimation Restriction**: If any contributing parent quantity is `ESTIMATED`:
   - Derived quantity evidence floor is capped at $\le 2$.
   - Kind cannot be `Kind.OBSERVED`.
4. **Complete Provenance**: Ancestry graph, source references, and restriction reasons are preserved in the calculation context.

---

## 5. Atlas Presentation & Shading Contract

The Atlas presentation contract provides MapLibre GL JS data-driven paint expressions and GeoJSON property decoration:

```json
{
  "fill-color": [
    "match", ["get", "quality_status"],
    "CURRENT", "#22C55E",
    "INCOMPLETE", "#EAB308",
    "STALE", "#F97316",
    "ESTIMATED", "#3B82F6",
    "UNAVAILABLE", "#94A3B8",
    "#94A3B8"
  ],
  "fill-opacity": [
    "match", ["get", "quality_status"],
    "CURRENT", 0.65,
    "INCOMPLETE", 0.60,
    "STALE", 0.70,
    "ESTIMATED", 0.60,
    "UNAVAILABLE", 0.45,
    0.45
  ]
}
```

- **Interactive Visual Preview**: Generated at [`docs/atlas-quality-shading-preview.html`](atlas-quality-shading-preview.html) and verifiable via automated browser tests.
- **API Endpoints**:
  - `GET /geo/{geo_id}/indicators`: Returns quantities with evaluated `quality_status`, `quality_color`, `quality_label`, and `shading`.
  - `GET /geo/{geo_id}/quality`: Returns multidimensional quality assessments and all secondary issue flags.
