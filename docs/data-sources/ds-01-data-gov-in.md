# Data Source: Open Government Data (OGD) Platform India (`data.gov.in`) (DS-01)

> **Verification Status**: `PENDING` (Under Verification)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**. Production-quality standards and correctness guarantees are mandatory; production requirements are never optional.
> **Core Rule**: No source is approved for production calculation until a human reviewer completes verification against defined acceptance gates. A successful API query or pagination run does not automatically mark a source as `GO`.

---

## 1. Identity & Publisher
- **Source ID**: `DS-01`
- **Official Name**: Open Government Data (OGD) Platform India
- **Publisher / Department**: National Informatics Centre (NIC), Ministry of Electronics and Information Technology (MeitY), Government of India (notified under the National Data Sharing and Accessibility Policy - NDSAP)
- **Official Portal URL**: [https://data.gov.in](https://data.gov.in)
- **Official Terms of Use**: [https://www.data.gov.in/terms-of-use](https://www.data.gov.in/terms-of-use)
- **Official GODL-India License**: [https://data.gov.in/Godl](https://data.gov.in/Godl) (and [https://data.gov.in/government-open-data-license-india](https://data.gov.in/government-open-data-license-india))
- **Official Resource Page**: [https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)
- **Official Catalog Page**: [https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)

---

## 2. Access Method & Authentication
- **Access Protocol**: REST API via HTTPS (`https://api.data.gov.in/resource/{resource_id}`) supporting JSON and XML response formats. The portal web interface also provides direct manual downloads for certain files (e.g., CSV, XLSX, visualisations).
- **Authentication on API Endpoints**:
  - Programmatic API access via `api.data.gov.in` requires an API key passed as a query parameter (e.g. `?api-key=YOUR_API_KEY&format=json`).
  - *Empirically Verified on Tested Endpoint*: An unauthenticated GET request to `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?format=json` was sent on 2026-10-19. The gateway (`tyk.io`) returned HTTP `400 Bad Request` with body:
    ```json
    { "error": "Authorization field missing" }
    ```
  - *Scope of Finding*: This HTTP 400 error confirms only that this particular unauthenticated API request was rejected by the gateway. It does not prove that every download method across the portal (such as direct web browser downloads) necessarily requires an API key.
- **Rate Limits & API Governance**:
  - The API endpoint is governed by the `tyk.io` API gateway.
  - The exact rate limits (e.g., requests per minute or daily call caps) are not published on the primary public landing page and remain **unverified**.
  - The API supports pagination via `limit` and `offset` parameters.
- **Platform Usage Terms**:
  - Standard government portal terms prohibit denial-of-service activities and malicious disruption. Any blanket assertions that web scraping is strictly prohibited or that rate limits depend on user account profiles remain **unverified** unless supported by applicable official terms or documentation.
- **Fallback Plan**: Pre-fetch and cache verified JSON/CSV snapshots in object storage (Cloudflare R2 / S3) so development, testing, and offline demos never rely on live government uptime.

---

## 3. Candidate Datasets Investigated (Provisional Leads)

> **Important**: All resource IDs, field names, and reporting parameters listed below are **provisional leads** gathered from secondary client wrappers, developer documentation, and public catalog listings. They must be validated against official dataset metadata or authenticated API responses during human inspection.

### Candidate A: Current Daily Price of Various Commodities from Various Markets (Mandi Prices)
- **Publishing Department**: Directorate of Marketing & Inspection (DMI), Ministry of Agriculture and Farmers Welfare (sourced via AGMARKNET).
- **Candidate Resource ID**: `9ef84268-d588-465a-a308-a864a43d0070` *(verified reachable via API smoke test and nationwide audit; see Section 5)*.
- **API Endpoint**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Authentication Required**: Yes, for this API endpoint.
- **Fields Observed in API Payload**:
  - `state`: State name string.
  - `district`: District name string.
  - `market`: Agricultural Produce Market Committee (APMC) mandi name.
  - `commodity`: Agricultural commodity name (e.g., Wheat, Potato, Onion, Rice, Wood).
  - `variety`: Commodity variety string.
  - `grade`: Quality grade string (e.g., Medium, FAQ).
  - `arrival_date`: Date of market arrival (DD/MM/YYYY).
  - `min_price`: Minimum wholesale price recorded (numeric).
  - `max_price`: Maximum wholesale price recorded (numeric).
  - `modal_price`: Most common/modal wholesale price recorded (numeric).
- **Price Unit Status & Evidence Comparison**:
  - *Related Official Portal Evidence*: The official e-NAM / AGMARKNET dashboard ([https://www.enam.gov.in/web/dashboard/agmarknet](https://www.enam.gov.in/web/dashboard/agmarknet)) displays commodity prices in rupees and includes an explicit, separate `Unit` field. Similarly, official commodity report PDFs (e.g. [AGMARKNET Potato Report](https://agmarknet.gov.in/Others/Potato.pdf)) report prices in Rs/quintal.
  - *Deficiency in OGD API Payload*: The OGD API response inspected for DS-01 does **not** include a `unit` field; prices are returned purely as raw numeric literals (e.g. `2414.47`).
  - *Production Calculation Gate*: **Do not assert that all records are INR/quintal without authoritative evidence connecting that unit to the fields in this exact endpoint.** Unverified prices must never enter financial calculations, break-even models, or business feasibility recommendations.
- **Geographic Granularity**: APMC market / district level across participating states.
- **Temporal Freshness & Date Discrepancies**:
  - The resource header, Catalog Info tab, and API payload exhibit date discrepancies (detailed in Section 5.3). Observed API payload dates (`arrival_date`) must be used to assess freshness; portal page update dates do not establish observation dates.
- **Suitability for ArthLens**: **Candidate for raw-material procurement modeling** in the **Small Food-Processing / Tiffin Unit** business template, subject to resolving unit confirmation and geographic gaps.
- **Limitations**:
  - Limited to agricultural and primary commodities traded in participating mandis; does not cover packaged retail FMCG items.
  - Mandi reporting is subject to seasonal, holiday, and reporting irregularities; missing data must never be interpreted as zero.

### Candidate B: All India Pincode Directory
- **Publishing Department**: Department of Posts, Ministry of Communications.
- **Provisional Resource ID**: `5c2f62fe-5afa-4119-a499-fec9d604d5bd` *(provisional lead; requires verification)*.
- **Provisional API Endpoint**: `https://api.data.gov.in/resource/5c2f62fe-5afa-4119-a499-fec9d604d5bd`
- **Authentication Required**: Yes, for this API endpoint.
- **Provisional Fields (to be confirmed)**:
  - `circlename`, `regionname`, `divisionname`, `officename`, `pincode`, `officetype`, `delivery`, `district`, `statename`.
- **Geographic Granularity**: Postal delivery office and PIN code level (~155,000 tabular records).
- **Suitability for ArthLens**: Candidate for **postal-code lookup and administrative-name mapping** (mapping 6-digit postal codes to post office, district, and state names).
- **Critical Geographic Limitation**:
  - This dataset is strictly a tabular directory. It does **not** provide geographic coordinates (latitude/longitude), boundary polygons, or spatial indexing.
  - It cannot replace GIS boundaries or road networks; its utility in ArthLens is limited to postal lookup and administrative validation.

### Candidate C: District-wise Primary Census Abstract (PCA) 2011 Data
- **Publishing Department**: Office of the Registrar General & Census Commissioner, India (ORGI), Ministry of Home Affairs.
- **Resource ID Status**: **No confirmed single OGD API resource ID** has been established on `data.gov.in` for the complete nationwide district PCA table. PCA tables on `data.gov.in` are fragmented across multiple state-specific and sectoral uploads.
- **Cross-Reference to DS-05**:
  - This candidate is retained as an **unverified cross-reference** to the dedicated **DS-05 (Census 2011 / LGD crosswalk)** investigation.
  - Complete, authoritative Primary Census Abstract tables are published directly in bulk tabular formats on [censusindia.gov.in](https://censusindia.gov.in) and via Local Government Directory crosswalks. Do not invent an OGD resource ID for data obtained directly from the Census portal.
- **Provisional Fields**: `State`, `District`, `Total_Households`, `Total_Population`, `Male_Population`, `Female_Population`, `Literates`, `Total_Workers`.
- **Known Limitations**: High staleness (Census 2011 data; requires mandatory `STALE` quality flag). Boundary reorganisation since 2011 requires reconciliations to current LGD codes.

---

## 4. Legal Terms, Licence & Attribution Evidence

### 4.1 Documented Licensing Basis
- **National Policy Framework**: National Data Sharing and Accessibility Policy (NDSAP).
  - The resource metadata explicitly displays: `"Released Under: National Data Sharing and Accessibility Policy (NDSAP)"`.
- **General Platform Terms**:
  - [Official OGD Terms of Use](https://www.data.gov.in/terms-of-use): The terms explicitly state that the **license metadata element of an individual dataset record governs its applicable terms**, unless otherwise noted.
  - [Official GODL-India Page](https://data.gov.in/Godl): Gazette-notified on February 13, 2017, the Government Open Data License – India grants a worldwide, royalty-free, non-exclusive license to use, adapt, publish, translate, display, distribute, and commercially or non-commercially exploit the data, subject to mandatory attribution, disclaimers of government liability, and specific exclusions (such as government insignia, personal data, and third-party IP).
- **Non-Commercial Scope & Legal Precondition**:
  - ArthLens is a noncommercial academic and portfolio project without monetization.
  - **Do not assume that noncommercial intent alone establishes legal permission to reuse data.** Lawful reuse requires adequate evidence that the applicable dataset terms or open license explicitly grant permission.

### 4.2 Resource-Specific Licensing Uncertainty
- The inspected Catalog Info screen confirmed release under NDSAP, but **did not render an explicit resource-specific license field**.
- A disabled "Catalog API" button exists on the portal UI; per project instructions, no further time will be spent attempting to troubleshoot or open this disabled control.
- While the platform states that public datasets published through OGD are governed by GODL-India, **legal review cannot be described as completed** until the individual resource's metadata element and any applicable exclusions are formally confirmed.

### 4.3 Draft Attribution Statement
Pursuant to the standard GODL-India attribution template, the draft citation for this dataset is formulated as follows:

> *"Current Daily Price of Various Commodities from Various Markets (Mandi), Directorate of Marketing & Inspection (DMI), Ministry of Agriculture and Farmers Welfare, published on Open Government Data (OGD) Platform India (https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi), catalog updated 18/10/2026 / resource header 19/10/2026, accessed 20/10/2026, licensed under Government Open Data License - India (https://data.gov.in/Godl). (Draft attribution; exact resource-specific attribution text pending confirmation)."*

---

## 5. Live Inspection, Smoke Tests & Nationwide Audit

### 5.1 Unauthenticated Endpoint Probe (Automated Check)
*(Empirical verification conducted on 2026-10-19)*
- **Inspection Date**: 2026-10-19
- **Inspector**: Antigravity AI (Task P0-1 Technical Pass)
- **Endpoint Tested**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?format=json`
- **Observed Result**: HTTP `400 Bad Request`, body `{"error": "Authorization field missing"}`, gateway header `X-Generator: tyk.io`.
- **Finding**: Confirmed that this particular unauthenticated request was rejected by the gateway.

### 5.2 Manual API Smoke Test (Prayagraj Pilot District)
*(Developer-performed smoke-test evidence, not an independently audited benchmark)*
- **Test Date**: 2026-10-20.
- **Tester**: Project Developer (authenticated inspection using locally stored API key).
- **Candidate Endpoint**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **General Query Result (`limit=2`)**:
  - Request succeeded and returned records.
  - Returned field names: `state`, `district`, `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`, `max_price`, `modal_price`.
  - Sample records: **Cabbage** and **Tomato** at Baripada APMC, Mayurbhanja, Odisha, with `arrival_date: 19/10/2026`.
- **District Filter Query (Prayagraj)**:
  - Query filtered for `filters[state.keyword]=Uttar Pradesh` and `filters[district]=Prayagraj` with `limit=10` returned 10 records (representing the requested limit, not total volume).
  - Records dated `19/10/2026` included: **Wood**, **Paddy(Common)**, **Wheat**, **Rice**, and **Onion**.
  - Markets in sample: **Prayagraj APMC**, **Ajuha APMC**, **Jasra APMC**, and **Lediyari APMC**.
- **Historical Name Query (Allahabad)**:
  - The same query using `filters[district]=Allahabad` returned zero records for this test.

### 5.3 Catalog Info Page Inspection
*(Human inspection of official portal page conducted on 2026-10-20)*
- **Catalog Page URL**: [https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)
- **Observed Catalog Info Metadata**:
  - Description: Daily wholesale maximum, minimum, and modal prices for various commodities.
  - Source: AGMARKNET portal.
  - Released Under: National Data Sharing and Accessibility Policy (NDSAP).
  - Updated On: `18/10/2026`.
- **Observed Discrepancies**:
  - Resource header displayed: `Updated On: 19/10/2026`.
  - Catalog Info tab displayed: `Updated On: 18/10/2026`.
  - API sample records displayed: `arrival_date: 19/10/2026`.
  - These are preserved as distinct observations across platform layers; do **not** infer guaranteed real-time synchronization from either portal date.

### 5.4 Nationwide API Snapshot Audit
*(Developer-performed audit results conducted on 2026-10-20 using script `audit_ds01.ps1`)*
- **Audit Date**: 2026-10-20.
- **Target Endpoint**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Execution & Pagination**:
  - Authenticated pagination loop querying `limit=1000` with increasing offsets.
  - The loop ran to completion without request failures or HTTP timeouts.
- **Empirical Snapshot Metrics**:
  - **API-Reported Total**: `16,080` records.
  - **Records Retrieved**: `16,080` records.
  - **Distinct Raw State/UT Labels**: `26`.
  - **Distinct District Labels**: `466`.
  - **Distinct Market Labels**: `1,624`.
  - **Distinct Commodity Labels**: `242`.
  - **Observed Arrival Dates**: All 16,080 parsed `arrival_date` values were identical: **`19/10/2026`**.
  - **Temporal Finding**: The response contained **no historical observation dates** in this particular snapshot.
- **Important Evidence Caveats**:
  - These are developer-performed audit results, not an independently audited benchmark.
  - Do not claim that the API contains only one day's data without further historical-access investigation (such as date-range filtering or archive endpoint checks).
  - Do not equate API pagination completion with comprehensive geographic coverage.
  - Do not claim that the feed has data for every Indian state, union territory, district, or market.

### 5.5 Geographic Coverage Analysis & Name Variations
- **Benchmark Source**: The official Government of India State/UT Web Directory ([https://www.india.gov.in/directory/web-directory/state-uts](https://www.india.gov.in/directory/web-directory/state-uts)) enumerates **36 official state and union territory administrative entities**.
- **Coverage Comparison (26 Present / 10 Absent in Snapshot)**:
  - The snapshot contained records corresponding to 26 state/UT labels.
  - **Ten entities had no matching labels in this snapshot**:
    1. Arunachal Pradesh
    2. Chandigarh
    3. Dadra and Nagar Haveli and Daman and Diu
    4. Jharkhand
    5. Ladakh
    6. Lakshadweep
    7. Manipur
    8. Mizoram
    9. Puducherry
    10. Sikkim
  - *Finding Scope*: These 10 entities were absent **in this observed snapshot only**. It must not be inferred that they are permanently absent from the source portal.
- **Observed Label Variations in Raw Data**:
  - `Chattisgarh` (observed) vs. `Chhattisgarh` (official)
  - `Keralam` (observed) vs. `Kerala` (official)
  - `Andaman and Nicobar` (observed) vs. `Andaman and Nicobar Islands` (official)
  - `NCT of Delhi` (observed) vs. `Delhi` (official)
- **Architectural Requirement**:
  - Robust **canonical-name normalization** (aliasing dictionary and LGD crosswalking) and **dynamic geographic coverage validation** are strictly required before nationwide application use.

---

## 6. Intended Application in ArthLens
- **Project Role & Nationwide Scope**:
  - **ArthLens is the final, deployable application**, developed as a noncommercial academic and portfolio project.
  - Its intended scope is **nationwide across India**.
  - It is not a disposable prototype. Production-quality standards, robust error handling, and evidence gating are mandatory.
  - **DS-01 is a candidate data source for nationwide agricultural wholesale price tracking.**
- **Fixture Segregation Rule**:
  - **Synthetic software-test fixtures used in automated unit and property tests must be strictly segregated from real government observations.**
  - Synthetic records, fakes, or illustrative mocks must **never** be represented as observed market data or exposed as production evidence.
- **Workflows Involved**:
  - **Loop A (Question to Verified Answer)**: Fetching published wholesale market indicators to answer factual economic questions.
  - **Loop B (Opportunity to Decision)**: Supplying empirical raw material procurement prices to the small food-processing / tiffin unit business cost model, and postal-code lookups for candidate site filtering.
- **Dependent Engines / Tools**:
  - `fetch_economic_indicator`
  - `DatasetIngestionPipeline` (Phase 2)
- **Resulting Quantity Definition Keys**:
  - `price.commodity.modal` (unit: to be confirmed via official metadata, e.g. `INR/quintal`, kind: `OBSERVED`)
  - `geo.pincode.lookup` (kind: `OBSERVED`)
- **Evidence Kind**: **`OBSERVED`** (for published empirical figures only; never applied to derived estimates, user assumptions, or test fixtures).

---

## 7. Decision Gate & Source Acceptance Requirements
- **Decision**: **`PENDING`** (Under Verification)
- **Status Rationale**:
  - The nationwide audit demonstrates that endpoint `9ef84268-d588-465a-a308-a864a43d0070` provides broad operational data (16,080 records across 466 districts and 26 states/UTs).
  - However, this establishes **broad coverage, not complete nationwide availability**.
  - 10 states/UTs were absent from the snapshot, naming variations exist, price units are omitted from the API payload, and resource-specific license confirmation remains pending.
  - **A successful API query or pagination run does not automatically mark the source as GO.**
- **Mandatory Source Acceptance Requirements (Before Production Calculation Approval)**:
  Before DS-01 can be marked `GO` and approved for production calculations in the final deployable product, all of the following criteria must be satisfied:
  1. **Applicable Data-Reuse Terms**: Authoritative evidence of applicable data-reuse terms (not assuming noncommercial intent alone grants permission).
  2. **Required Attribution Statement**: Final verified attribution statement formatted in accordance with source provider rules.
  3. **Authoritative Price Unit Confirmation**: The unit of measurement for `min_price`, `max_price`, and `modal_price` must be authoritatively established. Prices with unverified units **cannot enter financial calculations or derived recommendations**.
  4. **Exposed Geographic Coverage & Missing Data Policy**:
     - Actual geographic coverage must be measured and transparently exposed to the user (e.g. via the Economic Atlas data-quality overlay).
     - **Missing data must never be interpreted as zero.** If data for a district or commodity is absent, the system must report a data gap.
  5. **Freshness Checks & Outage Strategy**: Documented observation dates, freshness thresholds (`max_age_days`), and defined error/fallback behavior (cached S3/R2 snapshots) for platform outages.
  6. **Alternative Source Evaluation**: Alternative verified sources (such as direct AGMARKNET or e-NAM endpoints) must be evaluated where this source does not provide sufficient coverage.
- **Policy on Unmet Acceptance Criteria**:
  - **If DS-01 cannot satisfy these source-acceptance requirements, the blocking issue must be documented and a suitable alternative evaluated rather than silently relaxing the requirements.**
- **Next Human Actions to Resolve Outstanding Blockers**:
  1. Identify authoritative documentation connecting the price fields in endpoint `9ef84268-d588-465a-a308-a864a43d0070` to an explicit unit of measurement (e.g. ₹/quintal).
  2. Confirm whether the portal metadata API exposes an explicit `license` field for this resource.
  3. Implement canonical name mapping for the observed state label variations.
  4. Perform schema inspection on the Pincode Directory candidate (`5c2f62fe-5afa-4119-a499-fec9d604d5bd`).
- **Signed-off By**: Pending Human Review
- **Sign-off Date**: *Unsigned*
