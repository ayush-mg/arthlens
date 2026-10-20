# Data Source: Udyam Registration Statistics (DS-07)

> **Verification Status**: `NO-GO for Spatial Competitor POIs / DEFERRED for Macro Counts`
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, Part 2.2 Capability 30)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **REJECTED FOR SPATIAL COMPETITORS / DEFERRED FOR MACRO STATS**. Evaluated for local MSME competitor counts. Rejected because individual enterprise street locations are private and not publicly accessible.

---

## 1. Identity & Publisher

- **Source ID**: `DS-07`
- **Official Name**: Udyam Registration MSME Density Statistics
- **Publishing Authority**: Ministry of Micro, Small & Medium Enterprises (MoMSME), Government of India
- **Official Portal**: [https://udyamregistration.gov.in](https://udyamregistration.gov.in)
- **Dashboard**: [https://dashboard.msme.gov.in](https://dashboard.msme.gov.in)

---

## 2. Access Method & Data Constraints

- **Access Protocols**:
  - Interactive Smartboard / Dashboard reports viewable online.
  - Periodic aggregate CSV uploads on `data.gov.in` (e.g. *"District-wise Micro, Small and Medium Enterprises registered under Udyam"*).
- **Public API Availability**:
  - There is **no public open API** allowing automated query of individual registered micro-enterprises.
- **Privacy & Statutory Restrictions**:
  - Under Government of India MSME guidelines, detailed enterprise registration filings (individual owner names, Aadhaar linkages, exact street addresses, and turnover figures) are confidential, non-public data.
  - The public dashboard only exposes coarse **district and state aggregate totals** (e.g., total count of registered micro units in Prayagraj).

---

## 3. Fatal Limitation for Spatial Catchment Modeling

In **Loop B (Opportunity to Decision)**, the goal of competitor analysis is to locate competing businesses within a **10-minute to 30-minute travel-time isochrone** around candidate business sites:
- An aggregate number like *"Prayagraj has 34,000 registered micro-enterprises"* provides zero spatial coordinates and cannot determine whether a competitor exists within 500 meters of a candidate site.
- Attempting to downscale aggregate district counts to specific street corners would violate ArthLens's fundamental epistemic rule against fabricating spatial locations.

---

## 4. Operational Resolution in ArthLens

Pursuant to **Handbook Part 2.2 (Capability 30)**:
1. Spatial competitor counts around candidate sites are derived strictly from **DS-04 (OpenStreetMap)** POIs (`shop=*`, `amenity=*`) where exact GPS coordinates exist.
2. The UI renders the mandatory **OSM Completeness Caveat** acknowledging that unmapped or informal roadside competitors may not appear on the map.
3. Coarse district-level Udyam density totals are deferred to R1 as an optional background macro indicator.

---

## 5. Decision Gate

- **Decision**: **`NO-GO (for Spatial Competitors) / DEFERRED (for Macro Indicators)`**
- **Justification**:
  - Lack of geo-located point coordinates makes Udyam unsuitable for catchment-level competitor modeling.
  - OpenStreetMap POIs fulfill the spatial competitor requirement under documented completeness caveats.
- **Scope Impact**:
  - Dependent feature (point-level Udyam competitor overlay) is formally cut from MVP. Spatial competitor analysis is fulfilled exclusively by OSM POIs.
