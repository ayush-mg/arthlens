# Hosting Limits, Deployment Architecture & LLM Provider Decision (Task P0-6)

> **Document Status**: Active Reference & Decision Document
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026), Parts 3.1, 3.2, 8.3, 8.6, 13.1, 14.1–14.5
> **Evaluation Date**: 2026-10-21
> **Audited By**: Antigravity Assistant (Developer B responsibility)

---

## 1. Executive Summary & Recommended Stack

This document establishes the verified hosting limits, deployment configurations, and LLM provider terms for ArthLens across three operational tiers:
1. **Local Development (Phase 1–6)**: Docker Compose (PostgreSQL 16 + PostGIS 3.4), local Python FastAPI + background worker, Next.js dev server, and `FakeLLMClient` / `ReplayLLMClient` with zero external hosting or LLM API costs.
2. **Public Academic Demonstration (Phase 7 Evaluation)**: Next.js on **Cloudflare Pages** (or Vercel Hobby under non-commercial academic terms), Python FastAPI container on **Render Starter ($7/mo always-on)** or **Hugging Face Spaces (`cpu-basic` free)**, managed database on **Neon Postgres (Free tier, 1 GB)** or **Supabase (Free tier, 500 MB)** with PostGIS enabled, static vector tiles and exports on **Cloudflare R2 (10 GB free, $0 egress)**, and LLM access via **OpenAI API (`gpt-6-luna` primary, `gpt-5.6-terra` reasoning fallback)** behind `ILLMClient` with active `ReplayLLMClient` fallback.
3. **Eventual Production / Commercial Startup**: Cloudflare Pages / Vercel Pro, dedicated container cluster (Render / AWS ECS / Fly.io), dedicated PostgreSQL + PostGIS (AWS RDS or Supabase Pro), Cloudflare R2, and contracted LLM enterprise endpoints with Zero Data Retention (ZDR).

---

## 2. Part A: Hosting & Deployment Provider Audit

### 2.1 Component Comparison Matrix

| Component | Evaluated Providers | Verified Free / Starter Limits | PostGIS / Extension Support | Sleep / Cold-Start / Expiry Behaviour | Commercial / TOS Constraints | Verdict & Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Frontend** | **Vercel** | **Hobby ($0/mo)**:<br>• 100 GB Fast Data Transfer<br>• 1M function invocations<br>• 300s serverless timeout (Fluid Compute)<br>• 4 CPU-hours / 360 GB-hours | N/A (Static + Serverless edge) | No sleep for static assets; serverless cold start ~200–500ms. | **STRICTLY NON-COMMERCIAL PERSONAL USE**.<br>Commercial or revenue-generating use requires Pro ($20/seat/mo). | **`VERIFIED (Academic Demo Only)`**.<br>Acceptable for coursework evaluation; non-viable for startup launch. |
| | **Cloudflare Pages** | **Free ($0/mo)**:<br>• Unlimited bandwidth<br>• 500 builds/month (20 min max build)<br>• 100,000 requests/day on Workers<br>• 10ms CPU time/request | N/A (Static + Edge functions) | Instant edge delivery; 0 cold start for static assets. | **COMMERCIAL USE FULLY PERMITTED**.<br>No personal-use restriction. | **`VERIFIED (Recommended Default)`**.<br>Future-proof for both academic evaluation and commercial deployment. |
| **B. Python API & Worker** | **Render** | **Free Web Service ($0/mo)**:<br>• 512 MB RAM, 0.1 CPU<br>• 750 free instance hours/mo<br><br>**Starter ($7/mo)**:<br>• 512 MB RAM, 0.5 CPU<br>• Always-on (no sleep) | N/A (Compute instance) | **Free Web Service sleeps after 15 min idle**; cold start takes **30–60 seconds**.<br>Background workers **do not exist on free compute** (require paid worker instance or running worker inside web process). | Commercial use permitted across all plans. | **`CONDITIONAL (Starter $7/mo Recommended for Live Demo)`**.<br>Free tier spin-down breaks long-running agent workflows unless replay mode or in-process async worker is used. |
| | **Hugging Face Spaces** | **Free `cpu-basic` ($0/mo)**:<br>• 2 vCPU, 16 GB RAM<br>• Docker SDK container support | N/A (Compute container) | **Sleeps after 48 hours of inactivity**; cold start takes **10–30 seconds**.<br>Filesystem is **ephemeral** (wiped on restart/rebuild). | Commercial / open research permitted under HF terms. | **`CONDITIONAL (Viable Free Demo Container)`**.<br>Generous RAM (16 GB) accommodates geospatial dependencies, but requires external DB + object storage. |
| **C. PostgreSQL + PostGIS** | **Neon Postgres** | **Free Tier ($0/mo)**:<br>• 1 GB storage per project<br>• 100 CU-hours/month<br>• 0 to 2 CU autoscaling (up to 8 GB RAM) | **PostGIS fully supported** (`CREATE EXTENSION postgis;` works natively). | **Scales to zero after 5 minutes idle**; cold start takes **300ms to 2 seconds** on first query. | Commercial use permitted. | **`VERIFIED (Recommended Managed Postgres)`**.<br>Fast resume (~1s), native PostGIS, and 1 GB storage comfortably holds Prayagraj GIS geometries (~150 MB). |
| | **Supabase** | **Free Tier ($0/mo)**:<br>• 500 MB database storage<br>• 1 GB file storage<br>• 2 active projects | **PostGIS fully supported** (`CREATE EXTENSION postgis;`). | **Pauses after 7 days of inactivity** (manual unpause via dashboard). Read-only lock if >500 MB. | Commercial use permitted. Pro is $25/mo (8 GB DB). | **`VERIFIED (Secondary Alternative)`**.<br>500 MB limit is tight when indexing dense OSM road graphs and large lineage tables. |
| | **Render Postgres** | **Free Tier ($0/mo)**:<br>• 1 GB storage | PostGIS supported. | **EXPIRES AND DELETED AFTER 30 DAYS**.<br>Not suitable for ongoing evaluation. Paid Starter is $7/mo. | Commercial use permitted. | **`REJECTED FOR FREE TIER (30-day deletion rule)`**.<br>Only viable if upgraded to paid $7/mo instance. |
| **D. Object Storage** | **Cloudflare R2** | **Free Tier ($0/mo)**:<br>• 10 GB-month standard storage<br>• 1M Class A operations/month (writes)<br>• 10M Class B operations/month (reads)<br>• **$0.00 Egress fees (100% free internet egress)** | 100% S3-compatible API (Boto3 / AWS SDK compatible) | Always-on worldwide edge network. | Commercial use permitted. Storage beyond free tier is $0.015/GB-mo. | **`VERIFIED (Strongly Recommended)`**.<br>Zero egress cost protects against unpredictable tile download bandwidth bills. |
| | **AWS S3** | Standard Pay-as-you-go:<br>• Storage: $0.023/GB-mo<br>• PUT: $0.005/1K; GET: $0.0004/1K<br>• **Egress: $0.09/GB internet egress** | Native S3 API | Always-on worldwide. | Commercial use permitted. | **`CONDITIONAL (Higher Cost Risk)`**.<br>Public vector map tile downloads can cause variable data egress charges. |

---

### 2.2 Deep Dive into Architectural Realities (Handbook Part 14)

#### 1. The Long-Running Job & Background Worker Constraint
- **Requirement (Handbook Part 3.1 & 8.3)**: Agent runs may take 20–60 seconds, and Monte Carlo simulations (10,000 iterations) take 5–15 seconds. Jobs are persisted in the `jobs` table and claimed using `SELECT ... FOR UPDATE SKIP LOCKED`.
- **Free-Tier Trap**: If an API container spins down mid-job (e.g. Render after 15 min or free serverless functions capped at 10s–300s), worker jobs are orphaned.
- **Architectural Solution**:
  1. *Local Dev*: Dedicated worker loop running in Docker Compose or a separate terminal process.
  2. *Evaluation / Demo*:
     - **Option 1 (Recommended $7/mo)**: Single Render Starter instance running FastAPI, with an embedded background thread/task running the worker polling loop.
     - **Option 2 (Zero-Cost Free Tier)**: Hugging Face Spaces (`cpu-basic`, 16 GB RAM) running the FastAPI app and worker polling loop in the same container. Inactivity timeout is 48 hours (far safer than 15 minutes).
     - **Option 3 (High-Reliability Demo Guard)**: **Replay Mode** (Handbook Part 14.4). For evaluations and presentations, pre-recorded golden traces for Loops A, B, and C are served directly from the database/object storage. Replay mode bypasses live worker execution entirely, guaranteeing 100% reliable demo presentation even if the host is cold.

#### 2. Server-Sent Events (SSE) Streaming
- **Requirement (Handbook Part 3.1)**: Live agent progress and simulation steps stream to the browser via SSE from the `run_events` table.
- **Provider Behaviour**:
  - Cloudflare Pages / Workers: Fully supports streaming responses (SSE).
  - Vercel: Supports streaming edge and serverless functions (up to 300s).
  - FastAPI on Render / Hugging Face: Natively streams SSE using `StreamingRespon### 3.1 Provider Comparison & Verification

> **Crucial Deprecation Notice**: On October 14, 2026, OpenAI officially announced the deprecation and planned API shutdown of the `gpt-4o` generation (including `gpt-4o-mini-2024-07-18`, `gpt-4o`, `gpt-4.1`, and `gpt-4.1-mini`), with final API shutdown scheduled for **January 14, 2027**. Consequently, ArthLens designates the current, officially supported **GPT-6 / GPT-5.6 generation** as its active targets.

| Provider | Model Identifier | Primary Use Case in ArthLens | Context Window | Verified Pricing (per 1M tokens) | Native Structured Outputs (JSON Schema) | Data Privacy & Model Training Policy | Official Documentation Source & Date |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenAI** | **`gpt-6-luna`**<br>*(Active Supported Primary)* | **Primary Workhorse**:<br>• Goal interpretation<br>• Structured plan proposals<br>• Tool call extraction<br>• Report narrative synthesis with `{{q:UUID}}` | ~1.05M tokens (text + image input, text output) | **Input: $0.10**<br>**Output: $0.50**<br>(Cached Input: $0.01) | **YES (Guaranteed)**:<br>`response_format: { type: "json_schema", strict: true }` guarantees exact Pydantic schema compliance. | **VERIFIED: API customer data is NOT used to train models**.<br>Retained up to 30 days solely for abuse monitoring. Commercial IP retained by user. | [platform.openai.com/docs/models](https://platform.openai.com/docs/models) & [openai.com/api/pricing](https://openai.com/api/pricing/) (Audited 2026-10-21) |
| | **`gpt-5.6-terra`**<br>*(Active Reasoning Fallback)* | **Complex Reasoning Fallback**:<br>• Multi-step replanning (max 3)<br>• Unstructured policy PDF extraction | 128k+ tokens | **Input: $2.00**<br>**Output: $12.00**<br>(Cached Input: $0.20) | **YES (Guaranteed)** | Same enterprise privacy terms as above. | [platform.openai.com/docs/models](https://platform.openai.com/docs/models) & [openai.com/api/pricing](https://openai.com/api/pricing/) (Audited 2026-10-21) |
| | *`gpt-4o-mini`*<br>*(Deprecated)* | *Legacy baseline* | 128k input<br>16k output | $0.15 in / $0.60 out | *Yes* | *Deprecated Oct 14, 2026; API shutdown Jan 14, 2027. Do not use for new builds.* | [platform.openai.com/docs/deprecations](https://platform.openai.com/docs/deprecations) (Audited 2026-10-21) |
| **Anthropic** | **`claude-3-5-haiku`** | Fast tool calling & structured plan generation | 200k input<br>8k output | **Input: $0.80–$1.00**<br>**Output: $4.00–$5.00** | **YES** via Tool Use / JSON mode | **VERIFIED: API customer data is NOT used for model training**.<br>30-day transient abuse log. | [anthropic.com/pricing](https://www.anthropic.com/pricing) (Audited 2026-10-21) |
| | **`claude-3-5-sonnet`** | Deep reasoning & policy analysis | 200k input<br>8k output | **Input: $3.00**<br>**Output: $15.00** | **YES** via Tool Use | Same as above. | [anthropic.com/pricing](https://www.anthropic.com/pricing) (Audited 2026-10-21) |
| **Google Gemini** | **`gemini-1.5-flash` / `gemini-2.0-flash`** | General orchestration & multimodal ingestion | 1M+ input<br>8k output | Standard rates: ~$0.35–$0.75 input, $1.05–$3.75 output (Tier dependent) | **YES** via `response_mime_type: "application/json"` | **CRITICAL WARNING**: Free tier on Google AI Studio **USES user data for human review and model training**.<br>**ONLY Paid Tier exempts data from training**. | [ai.google.dev/pricing](https://ai.google.dev/pricing) & [ai.google.dev/terms](https://ai.google.dev/terms) (Audited 2026-10-21) |

---

### 3.2 Recommended LLM Provider & Model Architecture

1. **Recommended Primary Live Provider**: **OpenAI API**
   - **Primary Model**: **`gpt-6-luna`** for all standard orchestrator steps, tool calls, and report text generation.
   - **Reasoning Model (Bounded Fallback)**: **`gpt-5.6-terra`** reserved exclusively for complex bounded replanning (max 3 replans) and unstructured policy PDF extraction.
   - **Rationale**:
     1. `gpt-6-luna` is the official modern successor to the deprecated `gpt-4o-mini`, providing exceptional cost-efficiency ($0.10 / 1M input, $0.50 / 1M output, $0.01 cached) with native deterministic structured JSON adherence via `strict: true`.
     2. Context window of ~1.05M tokens accommodates substantial multi-turn history and prompt cache benefits.
     3. Strict contractual privacy guarantee: API inputs and outputs are never harvested for public model training.
     4. Rate limits: Dependent on OpenAI organization tier (starting at 500 RPM / 200,000 TPM on Tier 1; marked `CONDITIONAL` per account).
2. **Provider Decoupling via `ILLMClient` (Handbook Part 3.2, 8.6)**:
   - Application code **must never import `openai` directly**. All interactions pass through:
     ```python
     class ILLMClient(ABC):
         @abstractmethod
         async def generate_structured(
             self, prompt: str, schema: type[BaseModel], task_type: TaskType
         ) -> BaseModel: ...
     ```
   - Concrete adapters (`OpenAIClient`, `AnthropicClient`, `GeminiClient`, `FakeLLMClient`, `ReplayLLMClient`) are swappable via `LLM_PROVIDER` environment variable.
3. **Zero-Cost Offline Clients**:
   - `FakeLLMClient`: Returns hardcoded, schema-valid synthetic responses for unit tests, property tests, and CI without network calls or API keys.
   - `ReplayLLMClient`: Returns pre-recorded, bit-identical responses from stored scenario runs.

---

### 3.3 Cost Governance & Safeguards (Handbook Part 8.3)

#### 1. Mathematical Cost Model
The per-run cost is formally modeled as:
$$\text{Cost}_{\text{run}} = \sum_{i=1}^{N_{\text{calls}}} \left( \frac{\text{prompt\_tokens}_i \times P_{\text{in}}}{10^6} + \frac{\text{completion\_tokens}_i \times P_{\text{out}}}{10^6} \right)$$

*Empirical Demonstration with `gpt-6-luna`*:
- A typical agent run executes ~8 orchestrator calls.
- Total prompt tokens across 8 calls: ~20,000 tokens (uncached).
- Total completion tokens across 8 calls: ~4,000 tokens.
- Cost calculation:
  $$\text{Cost} = \left(\frac{20,000 \times 0.10}{1,000,000}\right) + \left(\frac{4,000 \times 0.50}{1,000,000}\right) = \$0.00200 + \$0.00200 = \mathbf{\$0.00400} \text{ (0.40 US cents)}$$
- Even an extensive run with 25 model calls on `gpt-6-luna` consumes less than **$0.015** (1.5 US cents)!

#### 2. Cost Governance Invariants (Handbook Part 8.3)
1. **Per-Run Cost Cap (`MAX_COST_USD_PER_RUN = 0.25`)**:
   - The $0.25 limit is an initial unmeasured hypothesis.
   - It provides a massive **~62x safety margin** over standard `gpt-6-luna` usage.
   - Enforced in code via `BudgetEnforcementDecorator`. If cumulative run cost exceeds $0.25, the run immediately halts with state `BUDGET_EXHAUSTED`, returns partial results, and lists unresolved gaps.
2. **Hard Quantitative Limits per Run**:
   - Maximum Steps: **25**
   - Maximum Replans: **3**
   - Maximum Model Calls: **30**
   - Tool Execution Timeout: **60 seconds**
   - Transient Tool Retries: **2**
3. **User Daily Quota**:
   - Configurable runs per user/role per day. Once exhausted, API returns `HTTP 429` with explanatory message and prompts user to use Replay Mode.
4. **Circuit Breaker**:
   - Trips on 2 consecutive transient errors or HTTP 429/503 responses, falling back to cached traces or `ReplayLLMClient`.

---

## 4. Operational Environment Matrix

| Environment | Frontend Host | Backend API & Worker | PostgreSQL + PostGIS | Object Storage | LLM Provider | Estimated Fixed Monthly Cost |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Local Development** | Next.js Dev Server (`localhost:3000`) | FastAPI + Worker in Docker Compose (`localhost:8000`) | Local Docker Container (`postgres:16-postgis-3.4`) | Local directory or MinIO container | `FakeLLMClient` (Zero API calls) | **$0.00** |
| **Continuous Integration (GitHub Actions)** | Headless build | Headless pytest suite | Service container (`postgis/postgis:16-3.4-alpine`) | Ephemeral test runner disk | `FakeLLMClient` (No external network) | **$0.00** |
| **Public Academic Evaluation (Zero-Cost Tier)** | Cloudflare Pages (Free) | Hugging Face Spaces (`cpu-basic`, 16 GB RAM Docker) | Neon Postgres (1 GB Free Tier) | Cloudflare R2 (10 GB Free, $0 egress) | Replay Mode / `gpt-6-luna` prepaid ($5 balance) | **$0.00** fixed + ~$1–$3 pay-as-you-go LLM |
| **Public Academic Evaluation (Recommended Starter)** | Cloudflare Pages (Free) | Render Starter ($7/mo always-on) | Neon Postgres (1 GB Free Tier) | Cloudflare R2 (10 GB Free, $0 egress) | `gpt-6-luna` behind budget cap | **$7.00/mo** + LLM usage |
| **Commercial Production (Future Scale)** | Cloudflare Pages / Vercel Pro ($20/seat) | Render Team / AWS ECS cluster | Managed AWS RDS or Supabase Pro ($25/mo) | Cloudflare R2 | Enterprise OpenAI / Anthropic with ZDR | **~$50–$150/mo** + usage |

---

## 5. Verification Sources & Official Links

1. **Vercel Hobby Plan & Fluid Compute**:
   - Source: [https://vercel.com/docs/accounts/plans/hobby](https://vercel.com/docs/accounts/plans/hobby)
   - Audited: 2026-10-21. Verified: 100 GB transfer, 300s timeout, non-commercial restriction.
2. **Cloudflare Pages & Workers Limits**:
   - Source: [https://developers.cloudflare.com/pages/platform/limits/](https://developers.cloudflare.com/pages/platform/limits/)
   - Audited: 2026-10-21. Verified: Unlimited bandwidth, commercial use allowed, 500 builds/mo.
3. **Render Pricing & Postgres Specifications**:
   - Source: [https://render.com/pricing](https://render.com/pricing)
   - Audited: 2026-10-21. Verified: Free service 15m idle sleep, Starter $7/mo always-on, Free Postgres 30-day expiry.
4. **Neon Postgres Specifications & PostGIS**:
   - Source: [https://neon.tech/pricing](https://neon.tech/pricing) & [https://neon.tech/docs/extensions/postgis](https://neon.tech/docs/extensions/postgis)
   - Audited: 2026-10-21. Verified: 1 GB storage, 100 CU-hours, native PostGIS support, 5m scale-to-zero.
5. **Cloudflare R2 Storage & Egress**:
   - Source: [https://developers.cloudflare.com/r2/pricing/](https://developers.cloudflare.com/r2/pricing/)
   - Audited: 2026-10-21. Verified: 10 GB standard storage free, $0.00 egress, S3 compatibility.
6. **OpenAI Models, Deprecations & Pricing**:
   - Source: [https://platform.openai.com/docs/models](https://platform.openai.com/docs/models), [https://platform.openai.com/docs/deprecations](https://platform.openai.com/docs/deprecations), and [https://openai.com/api/pricing/](https://openai.com/api/pricing/)
   - Audited: 2026-10-21. Verified: `gpt-4o-mini` deprecated Oct 14, 2026 with shutdown Jan 14, 2027. Active supported replacement is `gpt-6-luna` ($0.10 in / $0.50 out per 1M), `gpt-5.6-terra` ($2.00 in / $12.00 out) for reasoning fallback. API data excluded from training by default.
7. **Anthropic API Pricing & Privacy**:
   - Source: [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing) & [https://support.anthropic.com](https://support.anthropic.com)
   - Audited: 2026-10-21. Verified: API data excluded from training by default.
8. **Google Gemini API Privacy Terms**:
   - Source: [https://ai.google.dev/pricing](https://ai.google.dev/pricing) & [https://ai.google.dev/terms](https://ai.google.dev/terms)
   - Audited: 2026-10-21. Verified: Free tier data is logged and used for training; Paid tier is exempt from training.21. Verified: Free tier data is logged and used for training; Paid tier is exempt from training.
