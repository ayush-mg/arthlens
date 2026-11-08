# ArthLens Government Scheme Rules: Human Approval Record

**Authoritative Specification:** ArthLens Build Handbook v1.0 (Section 2.1, 2.2 #10, 6.8, 13.1 P0-2).  
**Record Date:** 2026-11-08  
**Repository:** `C:\arthlens`

---

## 1. Governance Policy & Fail-Closed Guardrails

Under the ArthLens Evidence and Policy Framework:
- No policy rule extracted from ministry guidelines may be presented to end users as officially certified advice without verified human sign-off.
- The rule engine evaluates all rules with Kleene three-valued logic (`TRUE`, `FALSE`, `UNKNOWN`).
- Each scheme's `is_approved_for_advice` property evaluates to `False` until an authorized human changes `approval_status` to `APPROVED` and records the `approved_by` and `approval_date`.
- If an unapproved rule is evaluated, the system outputs the structural eligibility evaluation alongside an explicit disclaimer:  
  *`"Rule extraction is candidate research only (HUMAN_REVIEW_REQUIRED). Not legal or financial advice."`*

---

## 2. Scheme Approval Records

### Scheme 1: PMFME (Pradhan Mantri Formalisation of Micro food processing Enterprises)
- **Scheme ID**: `scheme:pmfme:v1`
- **Issuing Ministry**: Ministry of Food Processing Industries (MoFPI), Government of India
- **Primary Source Document**: `docs/schemes/source_files/PMFME_Scheme_Guidelines_English.pdf`
- **Document Content Hash (SHA-256)**: `632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8`
- **Applicable Geography**: Nationwide; priority to One District One Product (ODOP) clusters
- **Target Enterprise Category**: Micro food processing units (<10 workers)
- **Extracted Financial Parameters**:
  - Subsidy Rate: 35% of eligible project cost
  - Subsidy Ceiling: ₹10,00,000 (₹10 Lakh) per enterprise
  - Minimum Beneficiary Contribution: 10% own equity
  - Balance Loan: Up to 90% via commercial bank term loan
  - Lock-in: 3 years in interest-free Subsidy Reserve Fund (SRF)
- **Required Evidence**:
  - `proof.identity` (Aadhaar / Voter ID)
  - `proof.enterprise_ownership_or_lease`
  - `proof.food_processing_activity`
  - `proof.own_equity_deposit`
- **Documented Ambiguities**:
  - Applicability of 35% subsidy rate to non-ODOP existing units across different State Nodal Agencies.
  - FSSAI registration grace period requirements for micro units.
- **Human Approval Status**: `HUMAN_REVIEW_REQUIRED` (Pending CA / Ministry review sign-off)

---

### Scheme 2: PMEGP (Prime Minister's Employment Generation Programme)
- **Scheme ID**: `scheme:pmegp:v1`
- **Issuing Ministry / Agency**: Ministry of MSME / Khadi & Village Industries Commission (KVIC)
- **Primary Source Document**: `docs/schemes/source_files/PMEGP_MSME_Official_Notification.pdf`
- **Document Content Hash (SHA-256)**: `90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb`
- **Applicable Geography**: Nationwide (Urban and Rural distinct subsidy tiers)
- **Target Enterprise Category**: New micro enterprises in manufacturing and business/service sectors
- **Extracted Financial Parameters**:
  - Maximum Project Cost (Manufacturing): ₹50,00,000 (₹50 Lakh)
  - Maximum Project Cost (Service): ₹20,00,000 (₹20 Lakh)
  - General Category Subsidy: 15% (Urban), 25% (Rural); Own Contribution: 10%
  - Special Category Subsidy (SC/ST/OBC/Women/PwD/Ex-Servicemen): 25% (Urban), 35% (Rural); Own Contribution: 5%
  - Lock-in: 3-year TDR with mandatory 3rd-party physical inspection before adjustment
  - Mandatory Gates: Udyam Registration and EDP training
- **Required Evidence**:
  - `proof.identity`
  - `proof.age` (minimum 18 years)
  - `proof.education_certificate` (8th pass certificate required if manufacturing > ₹10L or service > ₹5L)
  - `proof.special_category_certificate_if_applicable`
  - `proof.project_dpr`
- **Documented Ambiguities**:
  - The notification covers FY 2021-22 to FY 2025-26; continuation guidelines beyond March 2026 require an official extension circular.
  - Rural vs urban classification for semi-urban outgrowth wards outside municipal corporations.
- **Human Approval Status**: `HUMAN_REVIEW_REQUIRED` (Pending KVIC / MSME officer review sign-off)

---

### Scheme 3: PM-MUDRA (Pradhan Mantri Mudra Yojana)
- **Scheme ID**: `scheme:pm_mudra:v1`
- **Issuing Ministry / Department**: Department of Financial Services (DFS), Ministry of Finance, Government of India
- **Primary Source Document**: `docs/schemes/source_files/PMMY_Tarun_Plus_Notification_2024.pdf`
- **Document Content Hash (SHA-256)**: `601c7bf54125b2f29b47e24483b87431f4ba512b9d21f8a85f8c857753e1a0d8`
- **Applicable Geography**: Nationwide
- **Target Enterprise Category**: Non-corporate, non-farm micro and small enterprises
- **Extracted Financial Parameters**:
  - Shishu: Up to ₹50,000
  - Kishor: ₹50,001 to ₹5,00,000
  - Tarun: ₹5,00,001 to ₹10,00,000
  - Tarun Plus (October 2024 Notification): ₹10,00,001 to ₹20,00,000 for previous Tarun borrowers who have successfully repaid loans
  - Collateral: Nil (Credit guarantee cover provided under CGFMU)
  - Subsidy: None (pure credit instrument)
- **Required Evidence**:
  - `proof.identity`
  - `proof.business_address`
  - `proof.bank_statement`
  - `proof.past_repayment_record_if_tarun_plus`
- **Documented Ambiguities**:
  - Discretionary margin money requirements imposed by individual lending banks for Kishor/Tarun (up to 15%).
  - Variation in processing fees across public and private sector banks.
- **Human Approval Status**: `HUMAN_REVIEW_REQUIRED` (Pending Bank Credit Officer review sign-off)

---

## 3. Human Approval Sign-Off Checklist

The human reviewer must complete the following steps before modifying `approval_status`:
- [ ] Confirm source document PDF has not been superseded by a newer gazette notification.
- [ ] Verify that financial caps match current RBI and Ministry circulars.
- [ ] Sign off on the AST rule definitions in `backend/arthlens/policy/scheme_rules.py`.
- [ ] Record reviewer name, official designation, and date in `SCHEME_RULES_HUMAN_APPROVAL_RECORD.md`.

