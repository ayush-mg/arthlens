# ArthLens Pilot District & Business Template Selection Report

> **Task Reference**: Task P0-4 (Handbook Part 2.1, 7.3, 7.4, 13.1)
> **Evaluation Date**: 2026-10-21
> **Target Pilot District**: **Prayagraj, Uttar Pradesh** (LGD District Code `175`, Census 2011 Code `175`)
> **Selected Business Templates**:
> 1. **Neighbourhood Retail Grocery (Kirana / General Store)**
> 2. **Small Food-Processing / Tiffin Unit (Micro-Food Enterprise)**
> **Formal Architecture Record**: [ADR-008 in docs/DECISIONS.md](DECISIONS.md#adr-008-pilot-district-selection-prayagraj-up-and-business-template-selection)
> **Governance Notice**: P0-4 is a **Human-Owned (`A + B`)** gate. This document presents the technical evaluation and gate evidence. Formal adoption requires human developer sign-off.

---

## 1. Executive Summary & Gate Decision

In accordance with the **ArthLens Build Handbook (Part 2.1 and Part 7.3)**, the first deployable release (MVP) must focus on:
- Exactly **one pilot district**, confirmed through empirical evidence against the Section 7.3 Go/No-Go Gate.
- Exactly **two micro-enterprise business templates**, with complete mapping of required parameters, source documents, evidence categories, Pint units, and geographic/temporal resolutions.

### Gate Evaluation Summary for Prayagraj, UP:

| Gate Criterion (Part 7.3) | Required Standard | Supporting Evidence | Verified Empirical Finding | Gate Status |
| :--- | :--- | :--- | :--- | :---: |
| **A. Usable Road Graph & POIs** | Verified road graph and categorized POI counts in candidate district. | [`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md) | Live audit of central commercial Prayagraj (Civil Lines / Katra bounding box): **1,253 Nodes**, **202 Ways**, secondary road network, and commercial POIs (fast food, retail clothing, banks, jewellery). Daily Geofabrik mirrors verified. | **`PASS`** *(with OSM Completeness Caveat)* |
| **B. Population at Demand Resolution with as_of Date** | Sub-district or village resolution population with explicit date. | [`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md)<br>[`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md) | Official Census 2011 PCA crosswalked to LGD Directory: District total **5,954,391** across **8 Tehsils** with numeric LGD codes (Sadar, Soraon, Phulpur, Handia, Karchhana, Bara, Meja, Koraon). Explicit `as_of`: **2011-03-01**. | **`PASS`** *(with STALE flag & popweight_v1 requirement)* |
| **C. Three Official Policy Schemes** | Guidelines fetched, verified, hashed; parameters extracted by hand. | [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md)<br>[`docs/schemes/source_register.md`](schemes/source_register.md)<br>[`docs/schemes/parameter_register.md`](schemes/parameter_register.md) | **3 Schemes, 9 primary PDFs, SHA-256 hashed, 42 `SOURCE_SUPPORTED` parameters**: PMFME (MoFPI, 12 params), PMEGP (MoMSME, 17 params), PM-MUDRA (DFS/MoF, 13 params). | **`PASS`** |

**Recommendation to Developers A & B**: **APPROVE Prayagraj, Uttar Pradesh as the MVP Pilot District.**

---

## 2. Detailed Part 7.3 Pilot District Gate Evaluation

### 2.1 Criterion A: Road Network & POI Density
- **Candidate Geometry**: Prayagraj District, Uttar Pradesh (Central coordinate: ~25.448°N, 81.836°E).
- **Verified Empirical Facts**:
  - OpenStreetMap API v0.6 was queried on 2026-10-21 on a 400m x 400m commercial grid in central Prayagraj (`min_lon=81.834, min_lat=25.448, max_lon=81.838, max_lat=25.452`).
  - Observed: 1,253 Nodes, 202 Ways.
  - Secondary road corridors verified: `Subhash Chauraha` (Way 28785511), `Sardar Patel Marg` (Way 28785347).
  - Commercial POIs verified: McDonald's (Node 2057700937, `amenity=fast_food`), Trends (Node 9994440050, `shop=clothes`), Central Bank of India (Node 10089009816, `amenity=bank`), Fiona Diamonds (Node 10089118123, `shop=jewelry`).
- **Limitations & Architectural Mitigations**:
  1. *Sample Extent vs. District Scope*: The live OpenStreetMap API inspection tested a 400m x 400m commercial sample in Civil Lines/Katra to verify node-way topology and commercial POI tagging without exceeding public API limits. Bulk road network coverage for the broader district is provided by Geofabrik regional extracts (`uttar-pradesh-latest.osm.pbf`).
  2. *Two-Tier Resolution Policy (Handbook Section 7.4)*:
     - **Navigable Tier (Entire District)**: All 8 tehsils of Prayagraj District (LGD `175`) have official boundaries, numeric identifiers, and census demographics for navigation in the Economic Atlas.
     - **Analysable Tier (Initial Verified Core)**: High-density, fully connected road graphs and commercial POI clusters are empirically verified in the urban commercial core (Sadar Tehsil: Civil Lines, Katra, Chowk). Initial Loop B micro-enterprise site evaluations are targeted at this verified urban footprint.
  3. *Rural Completeness Asymmetry*: In peripheral rural tehsils (e.g. Bara, Koraon, Meja), primary/secondary highway vectors exist, but informal micro-enterprises (unregistered dhabas, kirana stalls) are unmapped in OSM. Pursuant to Handbook Part 2.2 (Capability 30), the Atlas UI renders the mandatory **OSM Completeness Caveat**:
     > *"Competitor density is derived from OpenStreetMap and reflects mapped physical establishments. Informal, temporary, or unmapped rural vendors may not be captured."*
  4. *Graph Disconnections*: Rural road ways may contain dead-ends or topological splits. Road network extraction in Phase 3 (`compute_catchment`) must extract the Largest Strongly Connected Component (SCC).
  5. *Uptime Guarantee*: All live Overpass calls are cached offline in `backend/fixtures/osm/prayagraj_roads.graphml` and GeoJSON fixtures. Offline demos run with 100% network independence.

### 2.2 Criterion B: Population Resolution & Temporal Support
- **Demographic Unit**: District 175 (Prayagraj / Allahabad), State 09 (Uttar Pradesh).
- **Verified Empirical Facts**:
  - Total District Population: **5,954,391** (Male: 3,131,807; Female: 2,822,584).
  - Total Households: 962,772. Average Literacy: 72.32%. Sex Ratio: 901.
  - Sub-District Breakdown (8 Tehsils with authoritative LGD codes):
    1. `Sadar Tehsil` (LGD `845`): Core urban tehsil containing Allahabad Municipal Corporation.
    2. `Soraon Tehsil` (LGD `843`): Northern agricultural/peri-urban tehsil.
    3. `Phulpur Tehsil` (LGD `844`): North-eastern industrial and agrarian belt.
    4. `Handia Tehsil` (LGD `846`): Eastern agricultural tehsil.
    5. `Karchhana Tehsil` (LGD `847`): Trans-Yamuna industrial/peri-urban tehsil.
    6. `Bara Tehsil` (LGD `848`): South-western rural tehsil.
    7. `Meja Tehsil` (LGD `849`): South-eastern rural tehsil.
    8. `Koraon Tehsil` (LGD `850`): Southern rural tehsil.
- **Explicit Temporal Support**:
  - Enumeration Reference Date: **2011-03-01** (Census of India 2011 Primary Census Abstract).
- **Resolution & Quality Policy**:
  - In accordance with Handbook Section 7.5, every population quantity derived from 2011 Census tables must carry the **`STALE`** quality flag.
  - Demand downscaling from Tehsil/District to catchment is performed strictly via registered method **`popweight_v1`** (Handbook Section 6.2):
    $$E_z = D_{\text{district}} \times \frac{\text{pop}_z \times w_z}{\sum_k (\text{pop}_k \times w_k)}$$
    This quantity enters the ledger as **`ESTIMATED`** and is subject to the conservation invariant ($\sum E_z = D$).

### 2.3 Criterion C: Policy Scheme Guidelines
- **Guidelines Verified**:
  1. **PMFME**: 4 official MoFPI documents, SHA-256 hashed. 12 parameters verified. Credit-linked capital subsidy (35%, max ₹10L), 10% own equity, 3-year Subsidy Reserve Fund lock-in.
  2. **PMEGP**: 2 official MoMSME/KVIC documents, SHA-256 hashed. 17 parameters verified. Margin money subsidy (15%–35%), ₹50L manufacturing cap, ₹20L service cap, mandatory Udyam registration, mandatory EDP training.
  3. **PM-MUDRA**: 3 official MoF/DFS documents, SHA-256 hashed. 13 parameters verified. Tarun Plus ceiling raised to ₹20L (effective 24.10.2024), 100% collateral-free, CGFMU credit guarantee cover up to ₹20L.
- **Geographic Applicability**: All 3 schemes are operational across Uttar Pradesh and active in Prayagraj district through Lead Bank (Bank of Baroda) and District Industries Centre (DIC).

---

## 3. Business Template Specification & Parameter Sources

### 3.1 Template 1: Neighbourhood Retail Grocery (Kirana / General Store)

- **Sector Classification**: Retail Trade & Non-Farm Micro-Services (NIC 4711).
- **Business Description**: Small-format neighbourhood retail store selling packaged groceries, dry provisions, toiletries, dairy products, and daily essentials.
- **Applicable Financial Schemes**:
  - **PM-MUDRA**: Primary financing mechanism. Collateral-free credit facility under Shishu (<₹50k), Kishor (₹50k–₹5L), or Tarun (₹5L–₹10L) for shopfitting and inventory stocking.
  - **PMEGP**: Eligible under "Business / Service Sector" (max project cost ₹20 Lakhs; Margin Money subsidy 15%–35% based on location and social category).
  - **PMFME**: **Disqualified / Ineligible**. PMFME explicitly excludes pure retail trading without food processing value-addition (PMFME Negative List Item 1).

#### Parameter Taxonomy for Template 1:

| Parameter Name | Pint Unit | Evidence Kind | Temporal / Geo Resolution | Primary Source / Basis |
| :--- | :--- | :--- | :--- | :--- |
| **Initial Capital Expenditure (Capex)** | `INR` | `USER_ASSUMED` / `ESTIMATED` | Point site | Shop shelving, billing counter, glass display, deep freezer, weighing scale, signage. Typical range: ₹2,00,000 to ₹8,00,000. |
| **Initial Inventory Buffer** | `INR` | `USER_ASSUMED` / `ESTIMATED` | Point site | 30–45 days stock of packaged FMCG and staples. Typical range: ₹1,50,000 to ₹5,00,000. |
| **Fixed Operating Cost (Opex)** | `INR/month` | `USER_ASSUMED` / `ESTIMATED` | Point site | Commercial store rent (₹5,000–₹20,000/mo depending on tehsil), commercial electricity (₹2,000–₹5,000/mo), store helper wage (₹8,000–₹12,000/mo). |
| **Gross Margin Percentage** | `dimensionless` (%) | `USER_ASSUMED` / `ESTIMATED` | Sectoral | Weighted average margin: 10%–18% on branded packaged FMCG; 18%–25% on loose pulses/grains. |
| **Cash Conversion Cycle (CCC)** | `days` | `USER_ASSUMED` / `ESTIMATED` | Enterprise | Days Inventory (25–35) + Days Receivables (5–10 for neighbourhood credit) - Days Payable (15–20 from distributors). |
| **Walking / Driving Catchment** | `minutes` | `CALCULATED` | Network | 15-minute walking catchment (default 800m–1.2km) computed via Dijkstra on OSM road graph (`DS-04`). |
| **Competitor Kirana Density** | `count` | `OBSERVED` | Catchment Polygon | Filtered OSM nodes/ways tagged `shop=convenience`, `shop=general`, `shop=supermarket` (`DS-04`). Subject to OSM Completeness Caveat. |
| **Household Demographic Base** | `persons` | `ESTIMATED` | Sub-district downscaled | Prayagraj sub-district census households downscaled via `popweight_v1` (`DS-05`, `STALE`). |
| **Financing Subsidy & Debt** | `INR`, `INR/month` | `POLICY_RULE` / `CALCULATED` | Statutory National | Subsidy rates and caps from `docs/schemes/parameter_register.md`; monthly EMI calculated via deterministic formula (`PMEGP-P02`, `PMEGP-P05..P08`, `MUDRA-P01..P05`). |

- **Upstream Dependency on DS-01 (Mandi Prices)**: **ZERO DEPENDENCY**. Retail grocery does not use daily agricultural mandi price feeds.

---

### 3.2 Template 2: Small Food-Processing / Tiffin Unit (Micro-Food Enterprise)

- **Sector Classification**: Micro Food Processing / Catering & Value Addition (NIC 1079 / 5621).
- **Business Description**: Small-scale commercial kitchen or value-added processing unit preparing packaged meals, dabba/tiffin services for office workers and students, or processing local produce (e.g. guava jelly/pulp under Prayagraj ODOP).
- **Applicable Financial Schemes**:
  - **PMFME**: **Primary targeted scheme** (MoFPI). 35% credit-linked capital subsidy up to ₹10 Lakhs; 10% beneficiary equity contribution; 3-year Subsidy Reserve Fund lock-in; access to DRP technical assistance (`PMFME-P11`).
  - **PMEGP**: Fully eligible under "Manufacturing Sector" (max project cost ₹50 Lakhs; Margin Money 15%–35%; mandatory EDP and Udyam).
  - **PM-MUDRA**: Working capital credit facility (Kishor / Tarun).

#### Parameter Taxonomy for Template 2:

| Parameter Name | Pint Unit | Evidence Kind | Temporal / Geo Resolution | Primary Source / Basis |
| :--- | :--- | :--- | :--- | :--- |
| **Initial Capital Expenditure (Capex)** | `INR` | `USER_ASSUMED` / `ESTIMATED` | Point site | Commercial gas ranges, exhaust system, wet/dry grinders, stainless steel tables, packaging sealer, delivery containers. Typical range: ₹3,00,000 to ₹12,00,000. |
| **Fixed Operating Cost (Opex)** | `INR/month` | `USER_ASSUMED` / `ESTIMATED` | Point site | Kitchen rent (₹6,000–₹18,000/mo), commercial LPG cylinders (₹4,000–₹10,000/mo), cook & delivery wages (₹15,000–₹30,000/mo), FSSAI license amortization. |
| **Packaging & Consumables Cost** | `INR/unit` | `USER_ASSUMED` / `ESTIMATED` | Per meal / pack | Eco-friendly meal trays, foil, delivery bags (₹6–₹12 per meal). |
| **Target Demand Generators** | `count` | `OBSERVED` | Catchment Polygon | Commercial offices, coaching institutes, university hostels, bank branches, hospitals mapped in OSM (`DS-04`). |
| **Delivery Travel Catchment** | `minutes` | `CALCULATED` | Network | 20–30 minute two-wheeler delivery catchment computed via Dijkstra on OSM road graph (`DS-04`). |
| **Competitor Food Outlets** | `count` | `OBSERVED` | Catchment Polygon | Filtered OSM nodes/ways tagged `amenity=fast_food`, `amenity=restaurant`, `amenity=cafe` (`DS-04`). |
| **Policy Capital Subsidy** | `INR` | `POLICY_RULE` | Statutory National | 35% of eligible project cost up to ₹10 Lakhs (`PMFME-P01`, `PMFME-P02`). |
| **Own Equity Margin** | `INR` (%) | `POLICY_RULE` | Statutory National | Minimum 10% of total project cost (`PMFME-P03`). |
| **Subsidy Holding Period** | `years` | `POLICY_RULE` | Statutory National | 3-year mandatory lock-in in interest-free Subsidy Reserve Fund (`PMFME-P05`). |

---

## 4. Critical Architecture Invariant: Gating of DS-01 Mandi Price Feeds

### Problem Statement:
- Dataset `DS-01` (`data.gov.in` AGMARKNET mandi wholesale price endpoint) currently has an unresolved status concerning price units (`PENDING`).
- The API response inspects raw numbers (e.g. `2414.47`) without returning an explicit `unit` field in the payload. While external AGMARKNET PDF publications report in Rs/quintal, the specific API endpoint does not provide programmatic unit confirmation.

### Binding Architectural Decision:
1. **Rule G2 / Invariant Enforcement**: In strict adherence to Handbook Part 0.2 and Section 4.7 (*"Incompatible or missing units cannot be combined; unverified numbers must never enter financial calculations"*), **automated raw material cost calculation from live DS-01 mandi price feeds is STRICTLY DISABLED in the MVP for Template 2.**
2. **Operational Fallback**:
   - The Tiffin / Food-Processing financial model requires the entrepreneur to supply their raw material unit cost directly as a `USER_ASSUMED` parameter (e.g. ₹35.00/meal or ₹45.00/kg).
   - Alternatively, the user may choose a curated, steward-approved static benchmark fixture tagged as `ESTIMATED`.
3. **Phase Boundary**: Dynamic ingestion and live price linking from `data.gov.in` remain gated until formal human verification of unit metadata and gateway governance is completed in Phase 2.

---

## 5. Human Governance Gate & Formal Sign-Off

- **Handbook Responsibility**: Task P0-4 is designated as **Human-Owned (`A + B`)** in Handbook Part 13.1.
- **Current Status**: **`APPROVED & ADOPTED (Human Developer Sign-Off 2026-10-21)`**
- **Record of Sign-Off**:
  - The human developer formally reviewed and approved the Prayagraj pilot district selection, the Two-Tier Geographic Coverage Policy (Navigable Tier district-wide vs. Analysable Tier in Sadar Tehsil urban commercial core), and the DS-01 safety restriction (disabling live agricultural mandi price feeds for micro-enterprise templates in MVP).
  - Gate P0-4 is formally closed.
