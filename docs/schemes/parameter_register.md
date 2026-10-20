# ArthLens Policy Parameter Register: PMFME, PMEGP, and PM-MUDRA

> **Task Reference**: Task P0-2 (Handbook Part 7, Section 7.2, Section 13.1)
> **Extraction Date**: 2026-10-20
> **Status**: SOURCE-SUPPORTED (MACHINE-EXTRACTED & CITATION-VERIFIED)
> **Authority**: Primary Government Gazettes, Ministry Notifications, and Master Operational Guidelines

---

## 1. Overview & Verification Taxonomies

To prevent policy hallucinations and confusion between different financial mechanisms (e.g. loans vs subsidies vs guarantees), ArthLens enforces strict financial mechanism typing and source traceability. Missing or unverified parameters are recorded explicitly as `UNKNOWN`. No figures are copied from secondary blogs or handbook illustrative text.

### 1.1 Verification Status Definitions

| Status Code | Meaning | Usage in ArthLens |
| :--- | :--- | :--- |
| `MACHINE_EXTRACTED` | Directly extracted by automated PDF parsing; pending textual citation check. | Raw extraction stage. |
| `SOURCE_SUPPORTED` | Extracted and verified against primary government document page/clause; fully cited. | Production candidate; ready for formal verification pass. |
| `INDEPENDENTLY_VERIFIED`| Independently cross-checked and signed off by two domain experts or legal counsel. | Production certified. |
| `CONFLICTING` | Contradictory rules exist between different ministry notifications. | Requires explicit resolution rule. |
| `UNKNOWN` | Parameter not specified in published guidelines. | Inferred values strictly prohibited. |

### 1.2 Financial Mechanism Classifications

| Mechanism Type | Legal & Accounting Definition | Example in Schemes |
| :--- | :--- | :--- |
| `CAPITAL_SUBSIDY` | Non-repayable government grant offsetting capital asset cost, typically back-ended. | PMFME 35% capital subsidy (max ₹10L). |
| `MARGIN_MONEY` | Subsidy held in interest-free Term Deposit / Reserve Fund for 3-year lock-in before adjustment against term loan. | PMEGP 15%–35% Margin Money. |
| `CREDIT_FACILITY` | Commercial term loan or working capital advance repayable with interest. | PM-MUDRA Shishu, Kishor, Tarun, Tarun Plus. |
| `CREDIT_GUARANTEE` | Third-party guarantee covering lender against default risk; no cash given to borrower. | CGFMU cover up to ₹20L under PMMY. |
| `SEED_CAPITAL` | Lump-sum revolving grant given to SHG federation, lent internally to members for working capital. | PMFME ₹40,000 seed capital per member. |

---

## 2. Scheme 1: PMFME (Pradhan Mantri Formalisation of Micro food processing Enterprises)

**Issuing Authority**: Ministry of Food Processing Industries (MoFPI), Government of India
**Target Beneficiaries**: Existing and new individual micro food processing enterprises, SHGs, FPOs, and producer cooperatives.
**Key Policy Principle**: One District One Product (ODOP) focus for common infrastructure, branding, and new units; existing micro enterprises eligible for upgradation regardless of ODOP status.

### 2.1 PMFME Parameter Table

| Parameter ID | Parameter Name | Exact Published Value | Unit & Currency | Financial Mechanism | Beneficiary / Business Category | Eligibility Conditions & Exclusions | Caps, Percentages & Contribution Rules | Document & SHA-256 Hash | Printed & PDF Page | Section / Clause Reference | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PMFME-P01` | Individual Subsidy Percentage | `35` | `%` | `CAPITAL_SUBSIDY` (Credit-Linked) | Individual Micro Food Processing Enterprises | Unincorporated; <10 workers; existing unit or new unit under ODOP; engaged in food processing. Excludes negative list. | 35% of eligible project cost. Back-ended credit linkage required. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 7 (PDF Page 7) | Section 5.1 | `SOURCE_SUPPORTED` |
| `PMFME-P02` | Individual Subsidy Maximum Ceiling | `10,00,000` | `INR (₹)` | `CAPITAL_SUBSIDY` (Credit-Linked) | Individual Micro Food Processing Enterprises | Individual ownership; one enterprise per family. | Maximum ceiling of ₹10.00 Lakh per enterprise. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 7 (PDF Page 7) | Section 5.1 | `SOURCE_SUPPORTED` |
| `PMFME-P03` | Individual Minimum Beneficiary Contribution | `10` | `%` | `OWN_EQUITY` | Individual Micro Food Processing Enterprises | Applicant must have legal ownership of unit or leased premises for minimum period. | Minimum 10% of total project cost must be contributed as beneficiary margin. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 7 (PDF Page 7) | Section 5.1.1 | `SOURCE_SUPPORTED` |
| `PMFME-P04` | Bank Loan Contribution | `Balance` (Up to `90`) | `%` | `CREDIT_FACILITY` | Individual Micro Food Processing Enterprises | Commercial bank credit appraisal standard. | Balance project cost (project cost minus own contribution) financed via commercial bank term loan. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 7 (PDF Page 7) | Section 5.1.1 | `SOURCE_SUPPORTED` |
| `PMFME-P05` | Subsidy Reserve Lock-in Period | `3` | `Years` | `SUBSIDY_HOLDING` | All credit-linked individual subsidy units | Beneficiary account must remain a standard asset and unit operational for 3 years. | Kept in interest-free Subsidy Reserve Fund (SRF) / TDR at lending bank; adjusted against loan after 3 years. If account becomes NPA, subsidy refunded to MoFPI. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 29 (PDF Page 29) | Section 13.2 | `SOURCE_SUPPORTED` |
| `PMFME-P06` | SHG Member Seed Capital | `40,000` | `INR (₹)` per member | `SEED_CAPITAL` | Self Help Group (SHG) members | Member must be presently engaged in food processing; commits to utilize for working capital and purchase of small tools. | Disbursed as grant from SRLM/SNA to SHG federation, which provides as internal revolving loan to members. Max ₹40,000/member. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 9–10 (PDF Pages 9–10) | Section 5.3.2, Section 5.3.6 | `SOURCE_SUPPORTED` |
| `PMFME-P07` | SHG Individual Member Capital Subsidy | `35` | `%` | `CAPITAL_SUBSIDY` (Credit-Linked) | Individual SHG Member as a single food processing unit | Minimum 3 years' experience in ODOP processing; sufficient funds for 10% own equity. | 35% of eligible project cost; maximum ceiling ₹10.00 Lakh. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 9 (PDF Page 9) | Section 5.3.3 | `SOURCE_SUPPORTED` |
| `PMFME-P08` | SHG Federation Capital Grant | `35` | `%` | `CAPITAL_SUBSIDY` (Credit-Linked) | SHG Federations | Engaged in collective processing of ODOP or allied agri-food products. | 35% credit-linked grant for capital investment. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 9 (PDF Page 9) | Section 5.3.4 | `SOURCE_SUPPORTED` |
| `PMFME-P09` | Common Infrastructure Grant Percentage | `35` | `%` | `CAPITAL_SUBSIDY` (Credit-Linked) | FPOs, SHGs, Cooperatives, State Agencies | Common facility for processing, assaying, sorting, grading, cold chain, or packaging; substantial ODOP utilization. | 35% credit-linked grant. Maximum ceiling ₹3.00 Crore (prescribed in operational norms). | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 10, 29 (PDF Pages 10, 29) | Section 5.4, Section 13.1 | `SOURCE_SUPPORTED` |
| `PMFME-P10` | Branding & Marketing Support Percentage | `50` | `%` | `GRANT` | FPOs, SHGs, Cooperatives, State SPVs | Focus on ODOP products; common branding, packaging, and marketing arrangement. | Up to 50% grant of eligible expenditure. Detailed DPR required. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 11–12 (PDF Pages 11–12) | Section 5.5 | `SOURCE_SUPPORTED` |
| `PMFME-P11` | District Resource Person (DRP) Incentive | `20,000` | `INR (₹)` | `SERVICE_FEE` | District Resource Persons (DRP) | Empanelled DRP assisting micro units in DPR preparation, bank loan sanction, and obtaining statutory registrations. | ₹20,000 per sanctioned bank loan: 50% upon bank loan sanction, remaining 50% after unit obtains FSSAI, Udyam, and GST registration. | `PMFME_Scheme_Guidelines_English.pdf` (`632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`) | Page 25 (PDF Page 25) | Section 9.3.8.4 | `SOURCE_SUPPORTED` |
| `PMFME-P12` | Negative List of Ineligible Activities | `18 distinct activities` | `CATEGORICAL_LIST` | `NEGATIVE_FILTER` | All applicants | Ineligible: Primary agricultural farming/production, slaughterhouse without meat processing, trading/retail without value addition, aerated synthetic beverages, beer/liquor/wine, gutkha/tobacco, standalone cold storage without processing unit. | Total disqualification from scheme funding. | `PMFME_Ineligible_Activities_Negative_List.pdf` (`803697eb0e4bbc3ec9533fd10bd6e6f9878222d8defa05f3d9c049f3f10df0a2`) | Page 1 (PDF Page 1) | Complete List | `SOURCE_SUPPORTED` |

---

## 3. Scheme 2: PMEGP (Prime Minister's Employment Generation Programme)

**Issuing Authority**: Ministry of Micro, Small & Medium Enterprises (MoMSME) / Khadi and Village Industries Commission (KVIC), Government of India
**Target Beneficiaries**: Individuals (age 18+), Self Help Groups, Institutions registered under Societies Registration Act 1860, Production Co-operative Societies, Charitable Trusts.
**Key Policy Principle**: Employment generation via new micro enterprises in manufacturing and service/business sectors. 15th Finance Commission Cycle (2021-22 to 2025-26) raised project cost ceilings and introduced mandatory Udyam registration.

### 3.1 PMEGP Parameter Table

| Parameter ID | Parameter Name | Exact Published Value | Unit & Currency | Financial Mechanism | Beneficiary / Business Category | Eligibility Conditions & Exclusions | Caps, Percentages & Contribution Rules | Document & SHA-256 Hash | Printed & PDF Page | Section / Clause Reference | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PMEGP-P01` | Maximum Admissible Cost — Manufacturing | `50,00,000` | `INR (₹)` | `MARGIN_MONEY_CAP` | New Micro Enterprises: Manufacturing Sector | Only for newly established units. Existing units not eligible under this clause. | Maximum project cost admissible for Margin Money subsidy is ₹50 Lakhs. Banks may finance balance above ₹50L without subsidy. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5 (PDF Page 5) | Clause 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P02` | Maximum Admissible Cost — Service / Business | `20,00,000` | `INR (₹)` | `MARGIN_MONEY_CAP` | New Micro Enterprises: Business / Service Sector | Only for newly established units. Excludes retail trading / negative list activities. | Maximum project cost admissible for Margin Money subsidy is ₹20 Lakhs. Banks may finance balance above ₹20L without subsidy. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5 (PDF Page 5) | Clause 2 | `SOURCE_SUPPORTED` |
| `PMEGP-P03` | General Category Own Contribution | `10` | `%` | `OWN_EQUITY` | General Category (Male, Urban/Rural) | Must be deposited into bank account before Margin Money claim generation. | Minimum 10% of total project cost contributed by beneficiary. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P04` | Special Category Own Contribution | `5` | `%` | `OWN_EQUITY` | Special Categories: SC / ST / OBC / Minorities / Women / Ex-servicemen / Differently abled / NER / Hill & Border areas / Transgenders | Caste/category certificate or relevant documentation required. | Minimum 5% of total project cost contributed by beneficiary. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P05` | General Category Urban Subsidy | `15` | `%` | `MARGIN_MONEY` | General Category: Urban Location | Unit physically located within municipal/urban jurisdiction. | 15% of admissible project cost provided as Margin Money. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P06` | General Category Rural Subsidy | `25` | `%` | `MARGIN_MONEY` | General Category: Rural Location | Unit physically located outside municipal urban boundaries / within rural panchayat. | 25% of admissible project cost provided as Margin Money. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P07` | Special Category Urban Subsidy | `25` | `%` | `MARGIN_MONEY` | Special Categories: Urban Location | SC, ST, OBC, Women, Minorities, PwD, Ex-Servicemen, NER, Hill/Border, Transgender in urban areas. | 25% of admissible project cost provided as Margin Money. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P08` | Special Category Rural Subsidy | `35` | `%` | `MARGIN_MONEY` | Special Categories: Rural Location | SC, ST, OBC, Women, Minorities, PwD, Ex-Servicemen, NER, Hill/Border, Transgender in rural areas. | 35% of admissible project cost provided as Margin Money. (Highest single subsidy rate under PMEGP). | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 4 (PDF Page 4) | Table 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P09` | Upgradation Admissible Cost — Manufacturing | `1,00,00,000` | `INR (₹)` | `MARGIN_MONEY_CAP` | Existing well-performing PMEGP / MUDRA manufacturing units | Unit must have fully repaid previous loan without default and show continuous profitability for past 3 years. | Maximum admissible project cost for second loan upgradation is ₹1.00 Crore. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5, 16 (PDF Pages 5, 16) | Table 2, Clause 11.29 | `SOURCE_SUPPORTED` |
| `PMEGP-P10` | Upgradation Maximum Subsidy — Manufacturing | `15,00,000` / `20,00,000` | `INR (₹)` | `MARGIN_MONEY` | Existing manufacturing units upgrading | Rate of subsidy is uniform 15% (all categories). | Max subsidy ₹15.00 Lakhs for general states; ₹20.00 Lakhs for NER and Hill States. Beneficiary contribution 10%. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5 (PDF Page 5) | Table 2, Clause 1 | `SOURCE_SUPPORTED` |
| `PMEGP-P11` | Upgradation Admissible Cost — Service / Business | `25,00,000` | `INR (₹)` | `MARGIN_MONEY_CAP` | Existing well-performing service / trading units | Unit must have fully repaid first loan; profitable for past 3 years. | Maximum admissible project cost for second loan upgradation is ₹25 Lakhs. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5, 16 (PDF Pages 5, 16) | Table 2, Clause 11.29 | `SOURCE_SUPPORTED` |
| `PMEGP-P12` | Upgradation Maximum Subsidy — Service / Business | `3,75,000` / `5,00,000` | `INR (₹)` | `MARGIN_MONEY` | Existing service units upgrading | Uniform 15% subsidy rate. Beneficiary contribution 10%. | Max subsidy ₹3.75 Lakhs for general states; ₹5.00 Lakhs for NER and Hill States. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 5 (PDF Page 5) | Table 2, Clause 2 | `SOURCE_SUPPORTED` |
| `PMEGP-P13` | Minimum Beneficiary Age | `18` | `Years` | `ELIGIBILITY_CRITERION` | Individual applicant | Any individual above 18 years of age. No upper age limit specified. | Minimum age threshold: 18 years. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 6 (PDF Page 6) | Eligibility Conditions | `SOURCE_SUPPORTED` |
| `PMEGP-P14` | Minimum Educational Qualification | `8th Standard Pass` | `LEVEL` | `ELIGIBILITY_CRITERION` | Individual applicants setting up projects above thresholds | Applies ONLY when: Manufacturing project cost > ₹10 Lakhs, or Service project cost > ₹5 Lakhs. Below these thresholds, NO minimum educational qualification required. | Formal 8th standard pass certificate required. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 6 (PDF Page 6) | Eligibility Conditions | `SOURCE_SUPPORTED` |
| `PMEGP-P15` | Mandatory Udyam Registration | `Mandatory` | `BOOLEAN` (`TRUE`) | `REGULATORY_GATE` | All PMEGP beneficiaries | Udyam Registration must be completed on the Udyam Portal before Margin Money can be adjusted in loan account. | Without Udyam registration, Financing Bank prohibited from adjusting Margin Money. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 1, 7, 26 (PDF Pages 1, 7, 26) | OM No: PMEGP/UdhyamReg./01/2023 | `SOURCE_SUPPORTED` |
| `PMEGP-P16` | Mandatory EDP Training | `Mandatory` | `PROCEDURAL_GATE` | `CAPACITY_BUILDING` | All PMEGP beneficiaries | Mandatory training (offline or via e-EDP portal) prior to release of Margin Money. | Non-compliance halts Margin Money adjustment. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 18 (PDF Page 18) | Clause 11.23 | `SOURCE_SUPPORTED` |
| `PMEGP-P17` | Margin Money Lock-in Period | `3` | `Years` | `SUBSIDY_HOLDING` | All PMEGP beneficiaries | Subsidy kept in interest-free Term Deposit Receipt (TDR) / Subsidy Reserve Fund (SRF) for 3 years at branch level. | Adjusted in loan account only after completion of 3-year lock-in and physical verification by 3rd-party agency confirming unit is active. | `PMEGP_MSME_Official_Notification.pdf` (`90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`) | Page 3, 14, 19 (PDF Pages 3, 14, 19) | Clause 11.18, 11.24 | `SOURCE_SUPPORTED` |

---

## 4. Scheme 3: PM-MUDRA (Pradhan Mantri MUDRA Yojana / PMMY)

**Issuing Authority**: Ministry of Finance (Department of Financial Services), Government of India
**Target Beneficiaries**: Non-corporate, non-farm small/micro enterprises across manufacturing, trading, services, and allied agricultural activities.
**Key Policy Principle**: Collateral-free and third-party guarantee-free credit facility refinanced by MUDRA Ltd and guaranteed under the Credit Guarantee Fund for Micro Units (CGFMU). Effective **24.10.2024**, the overall loan limit was expanded from ₹10 Lakh to **₹20 Lakh** via the creation of the **'Tarun Plus'** category.

> [!IMPORTANT]
> **Financial Distinction**: PM-MUDRA does NOT offer direct capital subsidies or margin money grants. It is strictly a credit and credit guarantee mechanism. Conflating MUDRA loans with capital grants is a fatal modeling error.

### 4.1 PM-MUDRA Parameter Table

| Parameter ID | Parameter Name | Exact Published Value | Unit & Currency | Financial Mechanism | Beneficiary / Business Category | Eligibility Conditions & Exclusions | Caps, Percentages & Contribution Rules | Document & SHA-256 Hash | Printed & PDF Page | Section / Clause Reference | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `MUDRA-P01` | Shishu Maximum Loan Limit | `50,000` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Micro-entrepreneurs / Startups | Non-farm micro enterprise; individual or group. Zero processing fee. | Loans up to ₹50,000. Collateral-free. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P02` | Kishor Minimum Loan Floor | `50,001` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Developing Micro Enterprises | Non-farm micro units needing growth capital. | Loans above ₹50,000. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P03` | Kishor Maximum Loan Ceiling | `5,00,000` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Developing Micro Enterprises | Non-farm micro units. Appraisal based on cash flows. | Loans up to ₹5.00 Lakh. Collateral-free. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P04` | Tarun Minimum Loan Floor | `5,00,001` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Established Micro Enterprises | Mature micro units looking for expansion capital. | Loans above ₹5.00 Lakh. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P05` | Tarun Maximum Loan Ceiling | `10,00,000` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Established Micro Enterprises | Mature micro units. Standard credit appraisal. | Loans up to ₹10.00 Lakh. Collateral-free. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P06` | Tarun Plus Minimum Loan Floor | `10,00,001` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Graduated Micro Enterprises | Mandatory prerequisite: Borrower must have previously availed and successfully repaid a loan under the 'Tarun' category. | Loans above ₹10.00 Lakh. (Created by Gazette w.e.f. 24.10.2024). | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P07` | Tarun Plus Maximum Loan Ceiling | `20,00,000` | `INR (₹)` | `CREDIT_FACILITY` (Term Loan / Working Capital) | Graduated Micro Enterprises | Successful repayment of prior Tarun loan; clean credit history. | Loans up to ₹20.00 Lakh. Raised overall PMMY ceiling to ₹20 Lakh. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P08` | Collateral & Third-Party Guarantee Requirement | `NIL` (`0`) | `INR (₹)` | `POLICY_INVARIANT` | All PMMY categories (Shishu, Kishor, Tarun, Tarun Plus) | Lending institutions are legally prohibited from demanding collateral security or third-party guarantee for PMMY loans. | 100% Collateral-free credit facility. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 3 (PDF Page 3) | Clause 1, Para 2(xi) | `SOURCE_SUPPORTED` |
| `MUDRA-P09` | CGFMU Credit Guarantee Cover Ceiling | `20,00,000` | `INR (₹)` | `CREDIT_GUARANTEE` | Member Lending Institutions (MLIs) | Guarantee extended to loans sanctioned by eligible MLIs complying with CGFMU notification norms. | Backed by Credit Guarantee Fund for Micro Units up to ₹20 Lakhs per borrower. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 3 (PDF Page 3) | Clause 3, Para 4 | `SOURCE_SUPPORTED` |
| `MUDRA-P10` | PMJDY Overdraft Guarantee Cover | `10,000` | `INR (₹)` | `CREDIT_GUARANTEE` | Pradhan Mantri Jan Dhan Yojana (PMJDY) account holders | Overdraft facility sanctioned in PMJDY account. | Eligible for credit guarantee cover under CGFMU up to ₹10,000. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 2, 3 (PDF Pages 2, 3) | Clause 1, 2, 3 | `SOURCE_SUPPORTED` |
| `MUDRA-P11` | SHG Loan Guarantee Cover Bracket | `> 10,00,000` to `20,00,000` | `INR (₹)` | `CREDIT_GUARANTEE` | Self Help Groups (SHGs) | SHGs meeting eligibility criteria prescribed by the Fund. | Covered under CGFMU guarantee for loans above ₹10 Lakh and up to ₹20 Lakh. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Page 3 (PDF Page 3) | Clause 2, Para 2(xii) | `SOURCE_SUPPORTED` |
| `MUDRA-P12` | Direct Capital Subsidy | `0` (None) | `INR (₹)` | `CAPITAL_SUBSIDY` | All PMMY categories | PMMY does not offer direct capital subsidy. MLIs may co-finance with other scheme subsidies where permissible. | ₹0 capital subsidy directly provided by PMMY. | `PMMY_Tarun_Plus_Official_Announcement.pdf` (`124749532d958079f5fb2c162afc60ea74b3b70054f74dafb5f944c8b43c33c8`) | Complete Gazette | Scheme Definition | `SOURCE_SUPPORTED` |
| `MUDRA-P13` | Processing Fee for Shishu Tier | `NIL` (`0`) | `INR (₹)` | `FEE_EXEMPTION` | Shishu tier borrowers (loans up to ₹50,000) | Lending institutions prohibited from levying processing or upfront charges on Shishu loans. | ₹0 processing fee. MLIs may charge nominal processing fee for Kishor, Tarun, Tarun Plus per internal board policies. | `PMMY_Tarun_Plus_Notification_2024.pdf` (`c6b69f099b0ede596df875721fdbb5540bd449cf6344fcd751ff981f66ad0b7d`) | Page 4 (PDF Page 4) | Section on Processing Charges | `SOURCE_SUPPORTED` |

---

## 5. Summary Parameter Counts & Verification Status

| Scheme Name | Primary Issuing Ministry | Number of Extracted Parameters | `SOURCE_SUPPORTED` | `INDEPENDENTLY_VERIFIED` | `UNKNOWN` / Pending Items |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **PMFME** | Ministry of Food Processing Industries (MoFPI) | **12** | 12 | 0 | 0 |
| **PMEGP** | Ministry of Micro, Small & Medium Enterprises (MoMSME) | **17** | 17 | 0 | 0 |
| **PM-MUDRA** | Ministry of Finance (Department of Financial Services) | **13** | 13 | 0 | 0 |
| **TOTAL** | — | **42** | **42** | **0** | **0** |

---

## 6. Policy Rules Flagged for Downstream ArthLens Engine

Before these parameters can be incorporated into automated eligibility engines or decision-support graphs in Phase 1+, the following rules must be accounted for:

1. **Lock-in Period Asset Status (PMEGP & PMFME)**:
   - Margin money / capital subsidy is *not immediately disbursed* to the applicant's pocket or credited directly to cancel the loan principal on day 1. It must sit in an interest-free Term Deposit Receipt / Subsidy Reserve Fund for exactly **3 years**.
   - If the business defaults or shuts down within 3 years, the subsidy is refunded back to the government nodal bank, leaving the entrepreneur with the full loan liability.
2. **Sequential Dependency for Tarun Plus (PM-MUDRA)**:
   - Borrowers cannot directly jump into the ₹10 Lakh to ₹20 Lakh bracket under MUDRA unless they demonstrate a track record of having availed and successfully repaid a prior loan under the Tarun category.
3. **Double Subsidy Bar**:
   - An entrepreneur cannot claim capital subsidy / margin money for the same project from both PMEGP and PMFME simultaneously.
4. **Negative Lists**:
   - PMEGP and PMFME maintain strict negative lists (e.g. tobacco, liquor, standalone slaughterhouse, pure retail trade without processing). The engine must enforce these negative filters before evaluating financial parameters.
