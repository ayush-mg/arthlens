# Data Source: Reserve Bank of India — Database on Indian Economy (RBI DBIE) (DS-02)

> **Verification Status**: `DEFERRED (R1)` (Deferred from Initial MVP Foundation)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 13.1)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **NON-ESSENTIAL / DEFERRED**. Planned for district banking credit context (BSR-1 / BSR-2 returns). Not an operational dependency for MVP cash-flow, break-even, or scheme eligibility calculations.

---

## 1. Identity & Publisher

- **Source ID**: `DS-02`
- **Official Name**: Basic Statistical Returns (BSR) — Quarterly Spatial Distribution of Deposits and Credit of Scheduled Commercial Banks
- **Publishing Authority**: Reserve Bank of India (RBI) / Department of Statistics and Information Management (DSIM)
- **Official Portal URL**: [https://dbie.rbi.org.in](https://dbie.rbi.org.in)
- **Documentation**: [https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Basic+Statistical+Returns](https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Basic+Statistical+Returns)

---

## 2. Access Method & Technical Architecture

- **Access Protocols**:
  - Interactive report builder via ASP.NET web forms on `dbie.rbi.org.in`.
  - Export formats: `.xlsx`, `.csv`, `.pdf`.
- **API Availability**:
  - The Reserve Bank of India does **not** provide a public, unauthenticated REST API endpoint for historical BSR district-level queries.
  - Automated programmatic ingestion requires simulating browser sessions, handling ASP.NET viewstates, or relying on third-party aggregators (e.g. EPWRF / Dataful).
- **Authentication**: Public web access; no formal API key system exists for developer consumption.

---

## 3. Geographic & Temporal Coverage

- **Geographic Granularity**: State, District, Population Group (Rural / Semi-Urban / Urban / Metropolitan), Bank Group (Public, Private, Foreign, RRB, SFB).
- **Temporal Frequency**: Quarterly BSR submissions (March, June, September, December).
- **Staleness Risk**:
  - Third-party mirrors and portal updates often lag publication by 6 to 18 months.
  - Historical district tables are periodically reclassified to reflect new district boundaries.

---

## 4. Legal Terms & Attribution

- **Licence Terms**: Official RBI public statistical data. Fair dealing for research, academic, and non-commercial analysis.
- **Attribution Requirement**:
  > *"Source: Reserve Bank of India (RBI) Database on Indian Economy (DBIE), Basic Statistical Returns (BSR)."*

---

## 5. Intended Role vs. MVP Feasibility

In the long-term vision, district credit-deposit ratios provide macroeconomic credit health context for the Atlas. However, in **MVP Loops A, B, and C**:
1. **Loan Arithmetic (Loop C)**: Loan repayment schedules, EMIs, moratorium periods, and subsidies are derived directly from statutory scheme rules (**DS-08: PMFME, PMEGP, PM-MUDRA**) and user capital inputs.
2. **Break-Even & Cash Flow (Loop B)**: Operational costs, revenues, and debt service coverage ratios do not depend on district SCB credit aggregates.
3. Making the initial Phase 0 acceptance contingent on reverse-engineering RBI's ASP.NET portal would expend engineering budget without unlocking any core MVP calculation.

---

## 6. Decision Gate

- **Decision**: **`DEFERRED (R1)`**
- **Justification**:
  - Lack of a public REST API makes dynamic ingestion brittle.
  - Not an active dependency for MVP feasibility, location comparison, or scheme eligibility workflows.
  - Scheduled for R1 inclusion as a pre-compiled static annual benchmark file.
- **Affected Features**:
  - District macro credit-deposit ratio indicator on the Atlas is deferred to R1. Feasibility modeling operates unimpeded.
