# ArthLens Brand Name Availability & Intellectual Property Clearance Report

> **Task Reference**: Task P0-3 (Handbook Section 1.0, Part 13.1)
> **Search Date**: 2026-10-21
> **Target Mark**: **"ArthLens"** (and phonetic/stylistic variants: *Arth Lens*, *Arthlens*)
> **Status**: **CONFLICT IDENTIFIED IN INDIAN CORPORATE & DOMAIN NAMESPACE**
> **Recommendation**: Permissible as an academic / coursework / research code name; **REBRANDING RECOMMENDED** prior to any commercial deployment or startup incorporation.

---

## 1. Executive Summary & Core Conflict Finding

Handbook Page 1 explicitly notes:
> *"Provisional name: ArthLens (name availability NOT verified)"*

Pursuant to the non-negotiable rule in Handbook Section 0.2 (*"Do not claim that a name is legally available merely because an exact-match search returns no result"*), a multi-registry audit was conducted across software package managers, code repositories, corporate entity databases, and intellectual property frameworks.

### Critical Finding:
An active commercial corporate entity operating in the Indian financial software sector already uses this exact mark:
- **Corporate Entity**: **Arthlens Technologies Private Limited**
- **Headquarters**: Bengaluru, Karnataka, India
- **Active Web Portal**: `https://arthlens.in`
- **Domain Registrations**: `arthlens.in`
- **Business Description**: A financial technology software tool designed for the Indian capital markets (NSE & BSE) that parses corporate filings and portfolio records to provide investors with analytical clarity (*"Arth"* = wealth/finance, *"Lens"* = clarity).
- **Contact**: `hello@arthlens.in`

---

## 2. Software Package Registry Probes (API Audit)

Empirical live API probes conducted on 2026-10-21 established the following package namespace statuses:

| Registry | Target Namespace | Live Probe URL | Query Result | Status |
| :--- | :--- | :--- | :---: | :--- |
| **PyPI** | `arthlens` | `https://pypi.org/pypi/arthlens/json` | HTTP 404 (Not Found) | **AVAILABLE** |
| **PyPI** | `arth-lens` | `https://pypi.org/pypi/arth-lens/json` | HTTP 404 (Not Found) | **AVAILABLE** |
| **npm** | `arthlens` | `https://registry.npmjs.org/arthlens` | HTTP 404 (Not Found) | **AVAILABLE** |
| **npm** | `@arthlens/core` | `https://registry.npmjs.org/@arthlens/core` | HTTP 404 (Not Found) | **AVAILABLE** |
| **GitHub** | `github.com/arthlens` | `https://api.github.com/users/arthlens` | HTTP 404 (Not Found) | **AVAILABLE (User/Org)** |
| **GitHub** | Repository Name Search | `https://api.github.com/search/repositories?q=arthlens` | HTTP 200 (Total count: 3) | **MIXED ADOPTION** |

### GitHub Repository Audit Details:
The 3 external public repositories matching `arthlens` on GitHub are:
1. `gustavomacedo-sketch/Arthlens`: A personal financial blog project in Portuguese.
2. `anshika55/Arthlens`: An unmaintained personal repository.
3. `harish-wipro/arthlens-web`: An inactive placeholder repository.
4. Active Project Remote: `https://github.com/ayush-mg/arthlens.git` (this project repository).

---

## 3. Indian Trademark Registry & Corporate Law Risk Assessment

### 3.1 Relevant Trademark Classes (Nice Classification)
Under the Indian Trade Marks Act, 1999, software decision-support tools span multiple classes:
- **Class 9**: Downloadable software, decision engines, mobile apps, artificial intelligence software.
- **Class 35**: Business management, market studies, commercial business feasibility research.
- **Class 36**: Financial affairs, financial evaluations, financial feasibility modeling, loan assessment tools.
- **Class 42**: Software as a Service (SaaS), cloud software hosting, scientific and technological services.

### 3.2 Statutory Legal Risk Analysis (Section 11, Trade Marks Act 1999)
Section 11(1) of the Indian Trade Marks Act prohibits the registration of a mark that is identical or deceptively similar to an earlier trade mark or established trade name for similar goods or services, creating a **likelihood of confusion** on the part of the public:
1. **Identical Name & Overlapping Field**: Both ArthLens (this project) and Arthlens Technologies Pvt. Ltd. operate in the field of Indian financial analysis software (*"Arth"* = economics/finance; *"Lens"* = analytical inspection).
2. **Prior Commercial Use**: Arthlens Technologies Pvt. Ltd. holds prior commercial adoption and an established `.in` top-level domain. Under Indian common-law trademark jurisprudence, **prior commercial use** takes precedence over subsequent registration.
3. **Passing Off Risk**: Any commercial deployment, public advertising, or institutional monetization under the name "ArthLens" in India would expose the creators to a potential action for passing off by Arthlens Technologies Pvt. Ltd.

---

## 4. Policy Decision & Recommendations

1. **For Academic & Coursework Phase (Phase 0 through Phase 7)**:
   - **PASS**: The name "ArthLens" remains fully viable as an internal academic project code name and GitHub repository title (`ayush-mg/arthlens`). Academic coursework and university evaluations carry zero commercial trademark infringement liability.
2. **For Startup Incorporation & Public Commercial Launch (Post-Phase 7)**:
   - **BLOCKED**: The founders must **NOT** attempt to incorporate an entity named "ArthLens Private Limited" in India or apply for an Indian trademark under Class 9/36 without obtaining formal written legal clearance or trademark assignment from Arthlens Technologies Pvt. Ltd.
   - **Recommended Future Action**: Conduct a formal rebranding exercise prior to public commercialization. Candidate derivative naming options to explore include:
     - *ArthDrishti*
     - *ArthPrashna*
     - *UdyamLens*
     - *NiveshLens*
     - *ArthBodh*
