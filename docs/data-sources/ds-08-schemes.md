# Data Source: Government Scheme Guidelines (DS-08)

> **Verification Status**: `GO` (Verified for Scheme Research, Parameter Extraction & Feasibility Modeling)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2, 13.1)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**. Production-quality standards and correctness guarantees are mandatory; production requirements are never optional.
> **Core Rule**: Scheme rules, financial parameters, contribution ceilings, and eligibility constraints must be derived exclusively from primary government notifications, gazettes, and operational guidelines. Secondary blogs or illustrative handbook text must never be treated as authoritative sources.

---

## 1. Identity & Issuing Authorities

- **Source ID**: `DS-08`
- **Official Name**: Central Government Entrepreneurship & MSME Scheme Guidelines (PMFME, PMEGP, PM-MUDRA)
- **Issuing Authorities**:
  1. **PMFME**: Ministry of Food Processing Industries (MoFPI), Government of India ([https://pmfme.mofpi.gov.in](https://pmfme.mofpi.gov.in))
  2. **PMEGP**: Ministry of Micro, Small & Medium Enterprises (MoMSME) / Khadi and Village Industries Commission (KVIC), Government of India ([https://msme.gov.in](https://msme.gov.in), [https://pmegp.msme.gov.in](https://pmegp.msme.gov.in))
  3. **PM-MUDRA**: Department of Financial Services (DFS), Ministry of Finance, Government of India ([https://financialservices.gov.in](https://financialservices.gov.in), [https://egazette.gov.in](https://egazette.gov.in), [https://www.mudra.org.in](https://www.mudra.org.in))
- **Detailed Registers**:
  - Primary Document & Hash Register: [`docs/schemes/source_register.md`](../schemes/source_register.md)
  - Extracted Policy Parameter Register: [`docs/schemes/parameter_register.md`](../schemes/parameter_register.md)
  - Local Source Files: [`docs/schemes/source_files/`](../schemes/source_files/)

---

## 2. Access Method & Local Preservation

- **Access Protocol**: Direct HTTPS download of official PDF gazettes and guidelines from verified government domains.
- **Authentication**: None required. All documents are public statutory notifications and official guidelines.
- **Local Preservation Strategy**:
  - All source PDFs are downloaded into [`docs/schemes/source_files/`](../schemes/source_files/).
  - Each file is cryptographically hashed using SHA-256.
  - The parameter register references exact PDF page numbers, printed page numbers, and clause identifiers to ensure 100% end-to-end traceability.

---

## 3. Geographic & Temporal Coverage

- **Geographic Coverage**:
  - **Nationwide (All States & UTs)**.
  - **PMFME**: Covers all 700+ districts with specific One District One Product (ODOP) designations; existing food processing units eligible across all districts.
  - **PMEGP**: Urban vs Rural classification (Panchayat areas qualify for rural higher subsidy rates). Special geographic provisions for NER, Hill States, and Border areas.
  - **PM-MUDRA**: Nationwide through all Commercial Banks, RRBs, Small Finance Banks, and MFIs.
- **Temporal Coverage & Validity**:
  - **PMFME**: Inception 2020-21, extended through 31st March 2027.
  - **PMEGP**: Master revision for the 15th Finance Commission Cycle (FY 2021-22 to FY 2025-26), amended 07.12.2023 for mandatory Udyam registration.
  - **PM-MUDRA**: Established 2015; updated by Extraordinary Gazette Notification S.O. 4658(E) dated 24.10.2024 raising loan ceiling to ₹20 Lakhs under 'Tarun Plus'.

---

## 4. Legal Terms, Licence & Attribution

- **Legal Nature**: Primary statutory notifications, executive orders, and gazettes published by Ministries of the Government of India.
- **Licence Terms**: Public government documents governed by National Data Sharing and Accessibility Policy (NDSAP) principles.
- **Attribution String**:
  > *Source: Ministry of Food Processing Industries (MoFPI), Ministry of Micro, Small & Medium Enterprises (MoMSME), and Department of Financial Services (DFS), Ministry of Finance, Government of India.*

---

## 5. Live Inspection & Verification Findings

- **Inspection Date**: 2026-10-20
- **Inspector**: Automated Extraction & Verification Pipeline (Task P0-2)
- **Primary Source Documents Verified**:

| Scheme | Document Title | Local File | Pages | SHA-256 Hash |
| :--- | :--- | :--- | :---: | :--- |
| **PMFME** | Scheme Guidelines (English) | [`PMFME_Scheme_Guidelines_English.pdf`](../schemes/source_files/PMFME_Scheme_Guidelines_English.pdf) | 33 | `632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8` |
| **PMFME** | Individual Micro Enterprises Guidelines | [`PMFME_Individual_Enterprises_Guidelines.pdf`](../schemes/source_files/PMFME_Individual_Enterprises_Guidelines.pdf) | 9 | `46495e2b2772997a59557bb4e1d96d791f1060a23674c4f2f569483218212d24` |
| **PMFME** | Individual & Group Guidelines (Revised) | [`PMFME_Individual_Group_Revised_2022.pdf`](../schemes/source_files/PMFME_Individual_Group_Revised_2022.pdf) | 5 | `7145c0e400c6aefef245a34b78d51e72fe11e570067753c53568496dba33bbd9` |
| **PMFME** | Negative List of Ineligible Activities | [`PMFME_Ineligible_Activities_Negative_List.pdf`](../schemes/source_files/PMFME_Ineligible_Activities_Negative_List.pdf) | 1 | `803697eb0e4bbc3ec9533fd10bd6e6f9878222d8defa05f3d9c049f3f10df0a2` |
| **PMEGP** | Master Operational Notification (15th FC) | [`PMEGP_MSME_Official_Notification.pdf`](../schemes/source_files/PMEGP_MSME_Official_Notification.pdf) | 29 | `90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb` |
| **PMEGP** | Foundational Guidelines | [`PMEGP_Scheme_Guidelines_indarun.pdf`](../schemes/source_files/PMEGP_Scheme_Guidelines_indarun.pdf) | 24 | `7645217492064a2e0805828cef63a47ef811a25cc86da46b52132c529f9a56bd` |
| **PMMY** | Extraordinary Gazette Notification (Tarun Plus) | [`PMMY_Tarun_Plus_Official_Announcement.pdf`](../schemes/source_files/PMMY_Tarun_Plus_Official_Announcement.pdf) | 3 | `124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8` |
| **PMMY** | Operational Details & Framework | [`PMMY_Tarun_Plus_Notification_2024.pdf`](../schemes/source_files/PMMY_Tarun_Plus_Notification_2024.pdf) | 7 | `c6b69f099b0ede596df875721fdbb5540bd449cf6344fcd751ff981f66ad0b7d` |
| **PMMY** | MUDRA Refinance Eligibility Norms | [`MUDRA_Eligibility_Criteria.pdf`](../schemes/source_files/MUDRA_Eligibility_Criteria.pdf) | 9 | `5ba7cf40fb2d79ea159f830cd57ec168b40290afb1426027a66a7411619caadc` |

---

## 6. Key Extracted Policy Parameters & Financial Mechanisms

A total of **42 structured policy parameters** were extracted across the three schemes:

1. **PMFME (12 Parameters)**:
   - **Mechanism**: `CAPITAL_SUBSIDY` (Credit-Linked).
   - Subsidy rate: **35%** of eligible project cost; ceiling of **₹10.00 Lakh** per unit.
   - Beneficiary contribution: Minimum **10%** own equity; balance **~55%–90%** commercial bank term loan.
   - Subsidy Reserve Lock-in: Kept in interest-free Subsidy Reserve Fund for **3 years** before adjustment.
   - SHG Seed Capital: **₹40,000 per member** for working capital / small tools.
   - Common Infrastructure Grant: **35%** up to ₹3.00 Crore.
   - Negative list: 18 ineligible non-processing activities.

2. **PMEGP (17 Parameters)**:
   - **Mechanism**: `MARGIN_MONEY` (Subsidy held in TDR for 3-year lock-in).
   - Maximum Admissible Cost (New Units): **₹50.00 Lakhs** (Manufacturing), **₹20.00 Lakhs** (Service).
   - General Category: Own contribution 10%; Margin Money = **15% (Urban)**, **25% (Rural)**.
   - Special Category (SC/ST/OBC/Women/Minorities/Ex-Servicemen/PH/NER/Hill/Border/Transgender): Own contribution 5%; Margin Money = **25% (Urban)**, **35% (Rural)**.
   - Upgradation (2nd Loan): Manufacturing up to **₹1.00 Crore** (max ₹15L / ₹20L NER subsidy); Service up to **₹25.00 Lakhs** (max ₹3.75L / ₹5L NER subsidy).
   - Regulatory Gates: **Mandatory Udyam registration** prior to subsidy adjustment; **mandatory EDP training**; minimum age 18; minimum 8th class pass for projects >₹10L (Mfg) / >₹5L (Service).

3. **PM-MUDRA (13 Parameters)**:
   - **Mechanism**: `CREDIT_FACILITY` (Collateral-free commercial term loan / working capital) backed by `CREDIT_GUARANTEE` (CGFMU via NCGTC). **NO capital subsidy**.
   - Categories & Ceilings:
     - **Shishu**: Loans up to **₹50,000** (zero processing fee).
     - **Kishor**: Loans above **₹50,000** and up to **₹5.00 Lakh**.
     - **Tarun**: Loans above **₹5.00 Lakh** and up to **₹10.00 Lakh**.
     - **Tarun Plus**: Loans above **₹10.00 Lakh** and up to **₹20.00 Lakh** (Effective 24.10.2024 for entrepreneurs with clean repayment of prior Tarun loans).
   - PMJDY Overdraft: Overdraft up to **₹10,000** covered under CGFMU guarantee.
   - Collateral requirement: **NIL** (legally prohibited from demanding collateral or third-party guarantee).

---

## 7. Intended Application in ArthLens

- **Workflows Involved**:
  - **Loop A (Feasibility & Viability Screening)**: Match entrepreneur inputs (location, sector, planned investment, caste/gender category) against scheme eligibility rules.
  - **Loop B (Capital Structure Optimization)**: Model optimal financing mix (own contribution, bank loan, margin money/subsidy) without violating double-subsidy prohibitions.
  - **Loop C (Decision Ledger & Evidence Provenance)**: Generate quantity records with evidence kind `POLICY_RULE` linking directly to document SHA-256 hashes and page references.
- **Evidence Kind**: `POLICY_RULE`.
- **Quality Rules**:
  - Missing parameters recorded as `UNKNOWN`. No inference permitted.
  - Subsidies and loans must never be combined into a single balance without distinguishing repayment liability.
  - 3-year subsidy reserve lock-in must be represented in cash-flow models.

---

## 8. Decision Gate

- **Decision**: **`GO`** (Approved for Scheme Modeling, Parameter Registers & Phase 1 Feasibility Rules).
- **Justification**:
  - 100% of required primary government source documents have been retrieved, hashed, and archived locally.
  - Key parameters extracted directly from official gazettes and ministry operational notifications with page/clause citations.
  - Clear separation established between capital subsidies, margin money, credit facilities, and credit guarantees.
- **Sign-off Date**: 2026-10-20
