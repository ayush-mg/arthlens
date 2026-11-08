# ArthLens Official Data Governance and Source Register

**Authoritative Specification:** ArthLens Build Handbook v1.0 (Part 3, 7.1, 7.2, 7.5, Appendix A.3).  
**Date:** 2026-11-08  
**Repository:** `C:\arthlens`

---

## 1. Verified Official Data Sources Register

| Source ID | Official Dataset Name | Publisher / Authority | Access Protocol | Update Frequency | Staleness Max Age | Licence & Reuse Terms | Geographic Scope | Data Vintage | Governance Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **DS-01** | District Credit-Deposit Ratio & Financial Aggregates | Reserve Bank of India (RBI DBIE) / Open Government Data Platform India (data.gov.in) | REST API / CSV bulk export | Annual / Quarterly | 365 days | Government Open Data License - India (GODL) | National / All Districts (including Prayagraj 120) | 2024 / FY23-24 | `HUMAN_REVIEW_REQUIRED` (Licence attribution sign-off pending) |
| **DS-04** | Road Network Graph & Commercial POI Amenities | OpenStreetMap Contributors | Overpass API / PBF extract | Continuous / Dynamic | 90 days | Open Database License (ODbL 1.0) | Pilot District: Prayagraj (`in:district:120`) | 2026 Q4 snapshot | `HUMAN_REVIEW_REQUIRED` (Attribution string approval pending) |
| **DS-05** | Primary Census Abstract (PCA) & LGD Crosswalk | Office of the Registrar General & Census Commissioner, India (ORGI) / Ministry of Panchayati Raj | CSV bulk export / LGD portal crosswalk | Decennial (Static) | 3650 days | Government Open Data License - India (GODL) | 800+ Districts across all States | Census 2011 (LGD mapped 2024) | `GO` (Verified against pilot Prayagraj) |
| **DS-08** | Central Government Scheme Operational Guidelines (PMFME, PMEGP, MUDRA) | Ministry of Food Processing Industries (MoFPI) / Ministry of MSME / Department of Financial Services (DFS) | Official Gazette PDFs / Scheme Portals | Annual / Parameter Notification | 365 days | Government Open Data License - India (GODL) | National / Target Enterprise Classes | 2022–2024 Guidelines | `HUMAN_REVIEW_REQUIRED` (Official scheme parameters review pending) |
| **DS-09** | Administrative Boundaries (Nation, State, District, Sub-district) | Data{Meet} Community Maps / Census 2011 Cartographic Boundaries | GeoJSON / PMTiles vector tiles | Static (Decennial) | 3650 days | Open Database License (ODbL 1.0) / Creative Commons BY-SA 4.0 | All India Districts & Subdistricts | Census 2011 / 2024 TopoJSON | `GO` (Verified against pilot Prayagraj) |

---

## 2. Quantity-Level Provenance & Source-Version Mapping

ArthLens strictly enforces **exact source-version mapping**:
1. Every empirical `Quantity` persisted in PostgreSQL contains a `source_refs` tuple linking directly to a registered `SourceVersionModel.id` (e.g. `("DS-05:census-2011-pca", "table/pca_120", "2026-11-07")`).
2. The [`resolve_quantity_provenance()`](file:///c:/arthlens/backend/arthlens/infra/provenance.py) function resolves the citation chain down to its root source versions, verifying content hashes and confirming `provenance_complete == True`.
3. If an input quantity lacks a valid source reference, its derived children inherit an incomplete provenance status and cannot achieve `FLOOR 1` (Direct Empirical Observation) or `FLOOR 2` (Official Government Statutory Policy).

---

## 3. Human-Review Packages for Data Stewardship

The following verification packages are prepared for human authorization. They are deliberately marked `HUMAN_REVIEW_REQUIRED` and will **never** be auto-approved without authorized human sign-off.

### Package 2.1: Open Government Data (DS-01) Licensing Sign-Off
- **Document URL**: `https://data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf`
- **Terms Summary**: GODL-India permits worldwide, royalty-free, non-exclusive use, reuse, and reproduction, subject to explicit attribution to the data provider (RBI / data.gov.in) and non-representation of government endorsement.
- **Action Required**: Human Legal / Stewardship approval of the exact attribution string displayed in the ArthLens Decision Dossier export footer.
- **Status**: `HUMAN_REVIEW_REQUIRED`

### Package 2.2: OpenStreetMap (DS-04) ODbL 1.0 Compliance
- **Document URL**: `https://opendatacommons.org/licenses/odbl/1-0/`
- **Terms Summary**: ODbL requires visible credit: *"© OpenStreetMap contributors"*, plus a Share-Alike obligation if a derivative database is produced and publicly distributed. ArthLens queries OSM dynamically as an external service without distributing raw transformed OSM planet dumps.
- **Action Required**: Human verification that cached Overpass graph snapshots comply with internal analysis guidelines.
- **Status**: `HUMAN_REVIEW_REQUIRED`

### Package 2.3: Central Government Scheme Guidelines (DS-08) Rule Certification
- **Document URLs**:
  - PMFME: MoFPI Guidelines `docs/schemes/source_files/PMFME_Individual_Enterprises_Guidelines.pdf`
  - PMEGP: KVIC/MSME Notification `docs/schemes/source_files/PMEGP_MSME_Official_Notification.pdf`
  - MUDRA: DFS/PMMY Circular `docs/schemes/source_files/PMMY_Tarun_Plus_Notification_2024.pdf`
- **Terms Summary**: Rules implemented in ArthLens define statutory subsidy calculations (e.g. 35% subsidy up to ₹10 Lakh for PMFME; 15%–35% margin money for PMEGP; ₹10–20 Lakh limits for Tarun Plus).
- **Action Required**: Qualified chartered accountant or scheme officer review of the AST rules and effective dates before public certification as advisory facts.
- **Status**: `HUMAN_REVIEW_REQUIRED`

