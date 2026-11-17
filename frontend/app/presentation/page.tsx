"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Play,
  Pause,
  Award,
  Layers,
  ShieldCheck,
  Cpu,
  Boxes,
  Database,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  Code2,
  GitBranch,
  Terminal,
  ExternalLink,
  BookOpen
} from "lucide-react";

interface SlideData {
  id: number;
  category: string;
  title: string;
  subtitle?: string;
  render: () => React.ReactNode;
}

export default function PresentationPage() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAutoplay, setIsAutoplay] = useState(false);

  const totalSlides = 15;

  const nextSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev < totalSlides - 1 ? prev + 1 : 0));
  }, [totalSlides]);

  const prevSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev > 0 ? prev - 1 : totalSlides - 1));
  }, [totalSlides]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
        e.preventDefault();
        nextSlide();
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        prevSlide();
      } else if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.key === "Home") {
        e.preventDefault();
        setCurrentSlide(0);
      } else if (e.key === "End") {
        e.preventDefault();
        setCurrentSlide(totalSlides - 1);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [nextSlide, prevSlide, totalSlides]);

  useEffect(() => {
    if (!isAutoplay) return;
    const timer = setInterval(() => {
      nextSlide();
    }, 12000);
    return () => clearInterval(timer);
  }, [isAutoplay, nextSlide]);

  const slides: SlideData[] = [
    // SLIDE 1: Title Slide
    {
      id: 1,
      category: "Academic Submission // IIIT Allahabad",
      title: "अर्थLens (ArthLens)",
      subtitle: "Sovereign Financial Operating System, Deterministic Integer-Paisa Khata & Staged AI Decision Intelligence Platform",
      render: () => (
        <div className="flex flex-col h-full justify-between py-2">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-400 font-mono text-xs">
              <Award className="w-3.5 h-3.5" />
              <span>IIIT ALLAHABAD &bull; COURSE PROJECT: OBJECT ORIENTED METHODOLOGIES</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-slate-100 tracking-tight font-serif">
              अर्थLens <span className="text-sky-400 font-sans font-light">(ArthLens)</span>
            </h1>
            <p className="text-lg md:text-xl text-sky-300/90 font-medium max-w-4xl leading-relaxed">
              Sovereign Financial Operating System, Deterministic Integer-Paisa Khata &amp; Staged AI Decision Intelligence Platform
            </p>
            <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
              An enterprise Object-Oriented Architecture demonstration binding commercial invoicing, perpetual FIFO inventory lots, algebraic double-entry ledgers, and human-in-the-loop AI governance.
            </p>
          </div>

          <div className="mt-6 p-6 rounded-xl border border-slate-700/60 bg-[#131b2a] shadow-xl backdrop-blur-md">
            <div className="text-xs font-mono uppercase tracking-widest text-emerald-400 mb-4 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              <span>Project Submission Credits // Team Members</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg border border-sky-500/30 bg-[#0b101b] border border-slate-700/60">
                <div className="text-base font-bold text-slate-100">AYUSH MISHRA</div>
                <div className="text-xs font-mono text-sky-400 font-semibold mt-1">IIT2025108</div>
                <div className="text-xs text-slate-400 mt-2">Architecture, Domain Design &amp; API Gateway</div>
              </div>
              <div className="p-4 rounded-lg border border-emerald-500/30 bg-[#0b101b] border border-slate-700/60">
                <div className="text-base font-bold text-slate-100">ABHAY PRATAP SINGH</div>
                <div className="text-xs font-mono text-emerald-400 font-semibold mt-1">IIT2025109</div>
                <div className="text-xs text-slate-400 mt-2">Financial Engine &amp; Decision Strategy Models</div>
              </div>
              <div className="p-4 rounded-lg border border-amber-500/30 bg-[#0b101b] border border-slate-700/60">
                <div className="text-base font-bold text-slate-100">MAYANK PURI</div>
                <div className="text-xs font-mono text-amber-400 font-semibold mt-1">IIT2025104</div>
                <div className="text-xs text-slate-400 mt-2">Presentation Tier, State Machines &amp; QA Harness</div>
              </div>
            </div>
          </div>
        </div>
      ),
    },

    // SLIDE 2: Problem Statement
    {
      id: 2,
      category: "Problem Statement",
      title: "The MSME Problem: Operational Chaos & Mathematical Drift",
      subtitle: "Over 80% of India's 63 Million MSMEs operate under severe operational and mathematical risks",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-5 rounded-xl border border-rose-500/30 bg-[#131b2a] shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-rose-400 font-bold text-sm mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span>1. Informal Credit Default Spiral</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
                <li>&bull; 63 Million Indian MSMEs contribute 30% of GDP and 45% of industrial output.</li>
                <li>&bull; Over 80% trade on oral credit recorded in physical paper diaries (<em>Bahi-Khata</em>).</li>
                <li>&bull; <strong>₹10.2 Lakh Crore ($120B)</strong> informal credit gap.</li>
                <li>&bull; Average receivables delay stretches to <strong>42 days</strong>, causing cascading insolvency when debtors default.</li>
              </ul>
            </div>
            <div className="text-[11px] font-mono text-rose-400/80 mt-2 pt-2 border-t border-rose-500/20">
              VULNERABILITY: Zero real-time debtor credit limits.
            </div>
          </div>

          <div className="p-5 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-amber-400 font-bold text-sm mb-2">
                <Cpu className="w-4 h-4" />
                <span>2. Floating-Point Rounding Corruption</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
                <li>&bull; Standard web apps use IEEE 754 floating-point numbers: <code className="text-amber-300">0.1 + 0.2 = 0.30000000000000004</code>.</li>
                <li>&bull; Over 50,000 invoices/year, fractional paisa rounding corrupts tax filings (GST) and audit verification.</li>
                <li>&bull; Disconnected billing apps drift from physical bank statements.</li>
              </ul>
            </div>
            <div className="text-[11px] font-mono text-amber-400/80 mt-2 pt-2 border-t border-amber-500/20">
              VULNERABILITY: Ledger reconciliation failure.
            </div>
          </div>

          <div className="p-5 rounded-xl border border-rose-500/30 bg-[#131b2a] shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-rose-400 font-bold text-sm mb-2">
                <Terminal className="w-4 h-4" />
                <span>3. AI Hallucination in Financial Operations</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
                <li>&bull; LLM wrappers attempt to answer balance sheet inquiries using stochastic token prediction.</li>
                <li>&bull; Generative AI models cannot reliably compute CAGR, loan amortization, or NPV.</li>
                <li>&bull; Hallucinated mathematical figures lead entrepreneurs into disastrous capital commitments.</li>
              </ul>
            </div>
            <div className="text-[11px] font-mono text-rose-400/80 mt-2 pt-2 border-t border-rose-500/20">
              VULNERABILITY: False confidence in fictitious numbers.
            </div>
          </div>

          <div className="p-5 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-sky-400 font-bold text-sm mb-2">
                <Boxes className="w-4 h-4" />
                <span>4. Rogue Autonomous Agents &amp; Tool Sprawl</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
                <li>&bull; Autonomous agents given direct write permissions mistakenly issue refunds or mutate stock.</li>
                <li>&bull; Fragmented workflows across paper, WhatsApp groups, and spreadsheets.</li>
                <li>&bull; Lack of an atomic unit of work across billing, inventory, and ledgers.</li>
              </ul>
            </div>
            <div className="text-[11px] font-mono text-sky-400/80 mt-2 pt-2 border-t border-sky-500/20">
              VULNERABILITY: Uncontrolled database state mutation.
            </div>
          </div>
        </div>
      ),
    },

    // SLIDE 3: Solution & 7-Step Pipeline
    {
      id: 3,
      category: "Platform Architecture",
      title: "The ArthLens Solution: 7-Step Sovereign Pipeline",
      subtitle: "Mathematical determinism, integer precision, and human-in-the-loop AI governance",
      render: () => (
        <div className="flex flex-col h-full justify-between py-2 space-y-4">
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-center">
            <span className="text-xs font-mono text-emerald-400 uppercase tracking-widest block mb-1">
              Core System Governing Equation
            </span>
            <div className="text-sm md:text-base font-mono font-bold text-slate-100">
              ArthLens = Sovereign Ledger (Integer Paisa) + Perpetual FIFO Inventory + Solvency Intelligence + Staged Human-Gated AI
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { step: "01", title: "Commercial Event", desc: "Invoice, PO, or capital loan inquiry ingested with strict schema validation." },
              { step: "02", title: "Integer Normalization", desc: "amount_paisa = int(round(val * 100)). Eliminates float rounding drift." },
              { step: "03", title: "Atomic Unit of Work", desc: "PostgreSQL transaction: verifies Debits == Credits & updates FIFO lots." },
              { step: "04", title: "Financial Intelligence", desc: "Real-time P&L, Balance Sheet, Altman Z&apos;-Score, and Working Capital Cycle." }
            ].map((s, i) => (
              <div key={i} className="p-3 rounded-lg border border-slate-700 bg-[#131b2a] shadow-xl">
                <div className="text-xs font-mono text-sky-400 font-bold mb-1">STEP {s.step}</div>
                <div className="text-xs font-bold text-slate-200 mb-1">{s.title}</div>
                <div className="text-[11px] text-slate-400 leading-snug">{s.desc}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { step: "05", title: "Scenario Laboratory", desc: "36-Month forward-looking simulation engine (Base / Bull / Stressed Monte Carlo)." },
              { step: "06", title: "Agentic Tool DAG", desc: "16 verified Python tools executed in an acyclic DAG. Zero database mutation." },
              { step: "07", title: "Staged Governance Gate", desc: "Proposals sit in PENDING_CONFIRMATION state. Requires explicit owner approval." }
            ].map((s, i) => (
              <div key={i} className="p-3 rounded-lg border border-amber-500/30 bg-[#131b2a] shadow-xl">
                <div className="text-xs font-mono text-amber-400 font-bold mb-1">STEP {s.step}</div>
                <div className="text-xs font-bold text-slate-200 mb-1">{s.title}</div>
                <div className="text-[11px] text-slate-400 leading-snug">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      ),
    },

    // SLIDE 4: 18 Workspace Chapters
    {
      id: 4,
      category: "Domain Modules",
      title: "Enterprise Capabilities: 18 Workspace Chapters",
      subtitle: "A unified Cosmic Orbit shell replacing fragmented tools with sovereign domain modules",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase tracking-wider flex items-center gap-2">
              <Boxes className="w-4 h-4" />
              <span>Commercial Operations</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
              <li><strong>02. Sales:</strong> Invoicing, credit limit checks, customer payments, returns.</li>
              <li><strong>03. Purchases:</strong> Vendor POs, goods receipt verification, payment release.</li>
              <li><strong>04. Inventory:</strong> Real-time stock, reorder alerts, FIFO lot layers.</li>
              <li><strong>05. Khata:</strong> Traditional double-entry customer &amp; vendor Bahi.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              <span>Financial Intelligence</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
              <li><strong>01. Overview:</strong> Executive pulse, liquid cash reserves, solvency ratios.</li>
              <li><strong>06. Finance:</strong> Real-time P&amp;L, Cash Flow, Balance Sheet, Liquidity.</li>
              <li><strong>10. Analytics:</strong> Working capital cycle, DSO/DPO aging, gross margins.</li>
              <li><strong>18. Constellation:</strong> 3D relational node graph across ledgers.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              <span>Strategic Decisions &amp; AI</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
              <li><strong>07. Decisions:</strong> Versioned decision models (v1.0.0), sensitivity replays.</li>
              <li><strong>08. Scenarios:</strong> 36-Month Scenario Laboratory (Bull / Bear / Stressed).</li>
              <li><strong>09. Goals:</strong> Strategic OKRs, milestones, revenue target tracking.</li>
              <li><strong>11. AI Agent:</strong> Deterministic Tool DAG Copilot with Staged Gate.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-rose-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-rose-400 font-bold uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              <span>Governance &amp; Administration</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
              <li><strong>12. Customers:</strong> Directory, credit limits, overdue recovery tracking.</li>
              <li><strong>13. Suppliers:</strong> Vendor procurement history &amp; AP balance management.</li>
              <li><strong>14. Reports:</strong> Exportable PDF &amp; CSV dossiers and tax ledgers.</li>
              <li><strong>15. Audit:</strong> Tamper-evident immutable audit log of all state deltas.</li>
              <li><strong>16. Members &amp; 17. Settings:</strong> RBAC role matrix &amp; tenant controls.</li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 5: Multi-Tier Architecture
    {
      id: 5,
      category: "System Architecture",
      title: "Multi-Tier System Architecture & Technology Stack",
      subtitle: "Clean Architecture adhering to strict domain separation and multi-tenant isolation",
      render: () => (
        <div className="flex flex-col h-full justify-between py-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
              <div className="text-xs font-mono text-sky-400 font-bold uppercase">
                Tier 1: Presentation Layer
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
                <li>&bull; <strong>Next.js 14 App Router</strong> (React 18 / TypeScript).</li>
                <li>&bull; <strong>Tactical Slate Design:</strong> Tailwind CSS &amp; Glassmorphism.</li>
                <li>&bull; <strong>Framer Motion:</strong> Fluid animation orchestration.</li>
                <li>&bull; <strong>Three.js:</strong> Interactive 3D Business Constellation.</li>
                <li>&bull; <strong>Optimistic UI:</strong> Auto-refreshing JWT Bearer tokens.</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
              <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
                Tier 2: Application &amp; Domain
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
                <li>&bull; <strong>FastAPI ASGI Gateway</strong> (Python 3.11+ / Uvicorn).</li>
                <li>&bull; <strong>Domain-Driven Design:</strong> Pure entities &amp; aggregates.</li>
                <li>&bull; <strong>BusinessService Facade:</strong> Coordinates 11 repositories.</li>
                <li>&bull; <strong>Security:</strong> Argon2id password hashing &amp; RBAC guards.</li>
                <li>&bull; <strong>AI Firewall:</strong> Gemini 1.5 Flash client + 16 local math tools.</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
              <div className="text-xs font-mono text-amber-400 font-bold uppercase">
                Tier 3: Persistence &amp; Infra
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
                <li>&bull; <strong>PostgreSQL 16:</strong> Managed cluster on Neon Serverless.</li>
                <li>&bull; <strong>SQLAlchemy 2.0:</strong> Async connection pool.</li>
                <li>&bull; <strong>Alembic Migrations:</strong> 26 automated migration scripts.</li>
                <li>&bull; <strong>Atomic Unit of Work:</strong> Zero orphaned records.</li>
                <li>&bull; <strong>Multi-Tenant Isolation:</strong> UUID query scoping (Zero IDOR).</li>
              </ul>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-sky-500/40 bg-sky-950/20 text-center">
            <span className="text-xs font-mono text-sky-400 font-bold block mb-1">
              UML ARCHITECTURE SPECIFICATION IN REPOSITORY
            </span>
            <p className="text-xs text-slate-300 max-w-4xl mx-auto leading-relaxed">
              Complete, dark-themed formal UML diagrams—including the <strong>Domain Class Diagram</strong>, <strong>Actors &amp; Use-Case Diagram</strong>, <strong>Commercial Order-to-Ledger Sequence Diagram</strong>, <strong>Staged AI Investigation Sequence Diagram</strong>, and <strong>State Lifecycle Machines</strong>—are cataloged in detail in the project&apos;s GitHub repository and <code>README.md</code>.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 6: OOM Core - Classes, Objects & Constructors
    {
      id: 6,
      category: "Object-Oriented Methodology",
      title: "OOM Core: Classes, Objects, Attributes & Constructors",
      subtitle: "Domain entities enforce data integrity and business invariants directly in constructors",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Domain Value Objects vs Anemic Models
            </div>
            <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
              <li>&bull; <strong>Immutable Value Objects:</strong> The <code className="text-sky-300 font-mono">Money</code> class is modeled as an immutable frozen dataclass, preventing state mutation after creation.</li>
              <li>&bull; <strong>Constructor Invariant Guards:</strong> The <code className="text-sky-300 font-mono">__post_init__</code> constructor enforces two-decimal Decimal quantization (ROUND_HALF_UP) and standardizes currency codes.</li>
              <li>&bull; <strong>Factory Methods:</strong> <code className="text-sky-300 font-mono">Money.from_float()</code> normalizes float values; <code className="text-sky-300 font-mono">Money.zero()</code> provides safe null representations.</li>
              <li>&bull; <strong>Operator Overloading:</strong> Polymorphic dunder methods <code className="text-sky-300 font-mono">__add__</code>, <code className="text-sky-300 font-mono">__sub__</code>, and <code className="text-sky-300 font-mono">__eq__</code> prevent currency mismatches.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#0b101b] border border-slate-700/60 font-mono text-xs overflow-x-auto space-y-2 text-slate-200">
            <div className="text-[11px] text-emerald-400 font-bold"># backend/arthlens/domain/business.py</div>
            <pre className="text-[11px] text-sky-200 leading-tight">
{`@dataclass(frozen=True)
class Money:
    amount: Decimal = field(default=Decimal("0.00"))
    currency: str = "INR"

    def __post_init__(self):
        # Enforce exact two-decimal quantization
        object.__setattr__(self, 'amount',
            Decimal(str(self.amount)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP))
        object.__setattr__(self, 'currency',
            (self.currency or "INR").upper())

    @classmethod
    def from_float(cls, val: float, curr="INR") -> 'Money':
        return cls(amount=Decimal(str(round(val, 2))),
                   currency=curr)

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise CurrencyMismatchException(
                f"Cannot add {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount,
                     currency=self.currency)`}
            </pre>
          </div>
        </div>
      ),
    },

    // SLIDE 7: Pillars 1 & 2 - Encapsulation & Abstraction
    {
      id: 7,
      category: "Object-Oriented Methodology",
      title: "OOM Pillars 1 & 2: Encapsulation & Abstraction",
      subtitle: "Shielding state mutations and decoupling domain logic from infrastructure details",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Pillar 1: Encapsulation
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Entities protect internal state from external tampering. State mutations are restricted to explicit domain methods.
            </p>
            <div className="p-3 rounded bg-slate-950 font-mono text-[11px] text-sky-200 space-y-1">
              <div>class SalesInvoice:</div>
              <div className="pl-3">def recalculate_totals(self) -&gt; None:</div>
              <div className="pl-6">subtotal = Money.zero(self.currency)</div>
              <div className="pl-6">for item in self.items:</div>
              <div className="pl-9">subtotal = subtotal + item.total_price</div>
              <div className="pl-6">self.subtotal = subtotal</div>
              <div className="pl-6">self.tax_amount = Money(...)</div>
              <div className="pl-6">self.total_amount = subtotal + tax</div>
            </div>
            <p className="text-xs text-slate-400">
              Invariant: Subtotal + Tax ALWAYS equals Total Amount. External callers cannot directly rewrite invoice totals.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Pillar 2: Abstraction
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              High-level domain services depend exclusively on Abstract Base Classes (ABCs), completely hiding SQL and ORM drivers.
            </p>
            <div className="p-3 rounded bg-slate-950 font-mono text-[11px] text-emerald-200 space-y-1">
              <div>class AbstractSalesInvoiceRepository(ABC):</div>
              <div className="pl-3">@abstractmethod</div>
              <div className="pl-3">def get_by_id(self, id: UUID) -&gt; Optional[SalesInvoice]:</div>
              <div className="pl-6">raise NotImplementedError</div>
              <div className="pl-3 mt-1">@abstractmethod</div>
              <div className="pl-3">def save(self, inv: SalesInvoice) -&gt; SalesInvoice:</div>
              <div className="pl-6">raise NotImplementedError</div>
            </div>
            <p className="text-xs text-slate-400">
              Decoupling: Domain services run identically in production with PostgreSQL 16 and in test suites with in-memory SQLite mocks.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 8: Pillars 3 & 4 - Inheritance & Polymorphism
    {
      id: 8,
      category: "Object-Oriented Methodology",
      title: "OOM Pillars 3 & 4: Inheritance & Polymorphism",
      subtitle: "Structured exception taxonomies and dynamic strategy dispatch",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Pillar 3: Inheritance
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              ArthLens organizes operational and security failures into an explicit, structured exception inheritance hierarchy:
            </p>
            <div className="p-3 rounded bg-slate-950 font-mono text-[11px] text-sky-200 space-y-1">
              <div>class ArthLensException(Exception): pass</div>
              <div className="pl-3">class DomainException(ArthLensException): pass</div>
              <div className="pl-6 text-rose-300">class InsufficientStockException(DomainException):</div>
              <div className="pl-9">def __init__(self, pid, req, avail): ...</div>
              <div className="pl-6 text-amber-300">class CreditLimitExceededException(DomainException): pass</div>
              <div className="pl-3">class SecurityException(ArthLensException): pass</div>
              <div className="pl-6 text-rose-300">class TenantAccessDeniedException(SecurityException): pass</div>
            </div>
            <p className="text-xs text-slate-400">
              Clean Exception Handling: Global FastAPI middleware intercepts base types and serializes HTTP status codes deterministically.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Pillar 4: Polymorphism
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Capital decision strategies implement a unified polymorphic interface, allowing dynamic evaluation dispatch:
            </p>
            <div className="p-3 rounded bg-slate-950 font-mono text-[11px] text-emerald-200 space-y-1">
              <div>class CapitalDecisionStrategy(ABC):</div>
              <div className="pl-3">@abstractmethod</div>
              <div className="pl-3">def evaluate(self, payload: dict) -&gt; Metrics: pass</div>
              <div className="mt-1">class MachinePurchaseStrategy(CapitalDecisionStrategy):</div>
              <div className="pl-3">def evaluate(self, payload: dict) -&gt; Metrics:</div>
              <div className="pl-6"># Computes capex depreciation &amp; tax shield</div>
              <div className="mt-1">class ProductExpansionStrategy(CapitalDecisionStrategy):</div>
              <div className="pl-3">def evaluate(self, payload: dict) -&gt; Metrics:</div>
              <div className="pl-6"># Computes inventory holding costs &amp; CAGR</div>
            </div>
            <p className="text-xs text-slate-400">
              Dynamic Dispatch: Decision engines invoke <code className="text-emerald-300">evaluate()</code> polymorphically regardless of strategy type.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 9: Class Relationships
    {
      id: 9,
      category: "Object-Oriented Methodology",
      title: "Class Relationships: Association, Aggregation & Composition",
      subtitle: "Object relationships model real-world business lifecycles and domain boundaries",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-rose-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-rose-400 font-bold uppercase">
              1. Composition (&bull;──)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              <strong>Strict Existential Lifecycle Binding:</strong> Child entities cannot exist without the parent aggregate root.
            </p>
            <ul className="text-xs text-slate-300 space-y-1">
              <li>&bull; <code className="text-rose-300">SalesInvoice &bull;── SalesInvoiceItem</code></li>
              <li>&bull; <code className="text-rose-300">Product &bull;── InventoryBalance</code></li>
            </ul>
            <div className="p-2.5 rounded bg-slate-950 font-mono text-[10.5px] text-rose-200">
              @dataclass<br/>
              class SalesInvoice:<br/>
              &nbsp;&nbsp;id: UUID<br/>
              &nbsp;&nbsp;items: List[SalesInvoiceItem] = field(...)
            </div>
            <p className="text-[11px] text-slate-400">
              Deleting an invoice destroys all its line items atomically.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase">
              2. Aggregation (&loz;──)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              <strong>Shared Lifecycle with Independent Existence:</strong> Objects belong to a container but outlive it.
            </p>
            <ul className="text-xs text-slate-300 space-y-1">
              <li>&bull; <code className="text-amber-300">BusinessWorkspace &loz;── BusinessMembership</code></li>
              <li>&bull; <code className="text-amber-300">BusinessWorkspace &loz;── Customer</code></li>
            </ul>
            <div className="p-2.5 rounded bg-slate-950 font-mono text-[10.5px] text-amber-200">
              @dataclass<br/>
              class BusinessWorkspace:<br/>
              &nbsp;&nbsp;id: UUID<br/>
              &nbsp;&nbsp;members: List[BusinessMembership] = field(...)
            </div>
            <p className="text-[11px] text-slate-400">
              Users exist independently; deleting a workspace preserves user profiles.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              3. Association (───)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              <strong>Loose Reference Coupling:</strong> Entities collaborate by foreign key references without ownership.
            </p>
            <ul className="text-xs text-slate-300 space-y-1">
              <li>&bull; <code className="text-sky-300">Customer ─── SalesInvoice</code></li>
              <li>&bull; <code className="text-sky-300">Product ─── SalesInvoiceItem</code></li>
            </ul>
            <div className="p-2.5 rounded bg-slate-950 font-mono text-[10.5px] text-sky-200">
              @dataclass<br/>
              class SalesInvoice:<br/>
              &nbsp;&nbsp;id: UUID<br/>
              &nbsp;&nbsp;customer_id: UUID # ASSOCIATION
            </div>
            <p className="text-[11px] text-slate-400">
              Customers exist before invoices are issued and remain after settlement.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 10: SOLID Part 1 (SRP, OCP, LSP)
    {
      id: 10,
      category: "Object-Oriented Methodology",
      title: "SOLID Principles: SRP, OCP & LSP",
      subtitle: "Ensuring single responsibility, extensible tool registries, and safe subtype substitution",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Single Responsibility (SRP)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every class has exactly one reason to change.
            </p>
            <ul className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <li>&bull; <strong>KhataLedgerEngine:</strong> Solely responsible for double-entry arithmetic and verifying <code className="text-sky-300">Sum(Debits) == Sum(Credits)</code>.</li>
              <li>&bull; <strong>InventoryCostService:</strong> Solely responsible for FIFO lot depletion and WAC revaluation.</li>
              <li>&bull; <strong>Argon2PasswordHasher:</strong> Solely responsible for cryptographic credential verification.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Open/Closed (OCP)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Open for extension, closed for modification.
            </p>
            <ul className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <li>&bull; <strong>BusinessToolRegistry:</strong> Allows new financial tools to be registered dynamically via decorators without altering the invocation engine.</li>
              <li>&bull; <code className="text-emerald-300">@registry.register(name=&apos;evaluate_loan&apos;, schema=...)</code></li>
              <li>&bull; Adding new decision tools requires zero edits to existing dispatch pipelines.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase">
              Liskov Substitution (LSP)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Subtypes must substitute for base types safely.
            </p>
            <ul className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <li>&bull; <code className="text-amber-300">PostgresSalesInvoiceRepository</code> completely conforms to <code className="text-amber-300">AbstractSalesInvoiceRepository</code>.</li>
              <li>&bull; Method signatures, return types, and exceptions match base contracts.</li>
              <li>&bull; Unit tests substitute an in-memory repository without breaking application logic.</li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 11: SOLID Part 2 (ISP & DIP)
    {
      id: 11,
      category: "Object-Oriented Methodology",
      title: "SOLID Principles: ISP & DIP",
      subtitle: "Fine-grained client protocols and constructor dependency injection",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Interface Segregation Principle (ISP)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Clients are never forced to depend on methods they do not invoke. Monolithic &quot;God Interfaces&quot; are eliminated.
            </p>
            <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
              <li>&bull; <strong>TokenRateLimiterProtocol:</strong> Exposes solely <code className="text-sky-300 font-mono">check_rate_limit(key)</code>.</li>
              <li>&bull; <strong>AuditTrailRecorder:</strong> Exposes solely <code className="text-sky-300 font-mono">record_audit_event(actor, action, delta)</code>.</li>
              <li>&bull; <strong>ReadOnlyKhataQuery:</strong> Exposes read operations (<code className="text-sky-300 font-mono">get_balance</code>, <code className="text-sky-300 font-mono">list_entries</code>) without mutation methods.</li>
            </ul>
            <p className="text-[11px] text-slate-400">
              Benefit: Reporting modules depend strictly on ReadOnlyKhataQuery, eliminating accidental database mutation risk.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-3">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Dependency Inversion Principle (DIP)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              High-level domain logic has zero dependencies on low-level database libraries. Both depend on abstract interfaces.
            </p>
            <div className="p-3 rounded bg-slate-950 font-mono text-[11px] text-emerald-200 space-y-1">
              <div>class BusinessService:</div>
              <div className="pl-3">def __init__(self,</div>
              <div className="pl-6">biz_repo: AbstractBusinessRepository,</div>
              <div className="pl-6">inv_repo: AbstractSalesInvoiceRepository,</div>
              <div className="pl-6">khata_repo: AbstractKhataRepository):</div>
              <div className="pl-9"># Injected abstractions, zero concrete SQL imports</div>
              <div className="pl-9">self.biz_repo = biz_repo</div>
            </div>
            <p className="text-[11px] text-slate-400">
              IoC Container: FastAPI injects concrete repository implementations via <code className="text-emerald-300">Depends()</code> providers at startup.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 12: 23 Design Patterns Catalog
    {
      id: 12,
      category: "Architecture Patterns",
      title: "Software Design Patterns Catalog: 23 Patterns",
      subtitle: "Comprehensive implementation of classic Gang of Four (GoF) and Enterprise Application patterns",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Creational Patterns (5)
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-snug">
              <li><strong>1. Singleton:</strong> DatabaseConnectionManager (shared connection pool).</li>
              <li><strong>2. Factory Method:</strong> Money.from_float() (safe creation with validation).</li>
              <li><strong>3. Builder:</strong> BusinessReportGenerator (PDF dossier assembly).</li>
              <li><strong>4. Registry:</strong> BusinessToolRegistry (16 math tools catalog).</li>
              <li><strong>5. Null Object:</strong> Money.zero() (prevents NoneType arithmetic crashes).</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Structural Patterns (8)
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-snug">
              <li><strong>6. Value Object:</strong> Money (Immutable decimal).</li>
              <li><strong>7. Aggregate Root:</strong> SalesInvoice (Consistency).</li>
              <li><strong>8. Façade:</strong> BusinessService (Unified API).</li>
              <li><strong>9. Adapter:</strong> serialize_invoice() (DTO JSON).</li>
              <li><strong>10. Decorator:</strong> @router.post(), @dataclass.</li>
              <li><strong>11. Composite:</strong> DecisionGraph (Nodes &amp; Edges).</li>
              <li><strong>12. Proxy:</strong> Depends(get_current_user).</li>
              <li><strong>13. Flyweight:</strong> SQLAlchemy Connection Pool.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase">
              Behavioral Patterns (10)
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 leading-snug">
              <li><strong>14. Unit of Work:</strong> Atomic transaction manager.</li>
              <li><strong>15. Strategy:</strong> CapitalDecisionStrategy.</li>
              <li><strong>16. Command:</strong> execute_tool(name, args).</li>
              <li><strong>17. Template Method:</strong> evaluate_with_constraints().</li>
              <li><strong>18. Observer:</strong> record_audit_event().</li>
              <li><strong>19. Chain of Resp:</strong> investigate() DAG.</li>
              <li><strong>20. State:</strong> InvoiceStatus &amp; ActionLifecycle.</li>
              <li><strong>21. Memento:</strong> DecisionEvaluationModel.</li>
              <li><strong>22. Specification:</strong> verify_workspace_access().</li>
              <li><strong>23. Iterator:</strong> FIFO inventory lot depletion.</li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 13: Financial Engineering & Mathematics
    {
      id: 13,
      category: "Financial Sovereignty",
      title: "Deterministic Financial Mathematics & Solvency",
      subtitle: "Prohibiting language models from performing arithmetic; verified by deterministic Python functions",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              1. Integer-Paisa Khata Invariant
            </div>
            <div className="p-2 rounded bg-slate-950 font-mono text-xs text-sky-200">
              paisa = floor(amount * 100 + 0.5)<br/>
              Sum(Debits) == Sum(Credits) [Delta = 0]
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every invoice, receipt, and tax deduction preserves conservation of value across all accounts without IEEE 754 float drift.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              2. Perpetual FIFO Inventory Lot Accounting
            </div>
            <div className="p-2 rounded bg-slate-950 font-mono text-xs text-emerald-200">
              New WAC = (Q_curr*WAC_curr + Q_in*Cost_in) / (Q_curr + Q_in)
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Oldest purchased inventory lots are depleted first upon commercial sales order fulfillment. Cost of Goods Sold (COGS) is locked.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase">
              3. Inflation-Adjusted Real NPV &amp; CAGR
            </div>
            <div className="p-2 rounded bg-slate-950 font-mono text-xs text-amber-200">
              Real NPV = Real Return - Discounted Repayment<br/>
              CAGR = [(Expected_Return / Principal)^(1/t) - 1] * 100%
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Prevents inflation-induced financial optical illusions by discounting loan cash flows by the national inflation rate (6%).
            </p>
          </div>

          <div className="p-4 rounded-xl border border-rose-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-rose-400 font-bold uppercase">
              4. Altman Z&apos;-Score for MSME Solvency
            </div>
            <div className="p-2 rounded bg-slate-950 font-mono text-xs text-rose-200">
              Z&apos; = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Calibrated for private manufacturing &amp; service enterprises. Z&apos; &gt; 2.90 Safe | 1.23 - 2.90 Grey | Z&apos; &lt; 1.23 Distress.
            </p>
          </div>
        </div>
      ),
    },

    // SLIDE 14: System Resilience & Security
    {
      id: 14,
      category: "Production Operations",
      title: "System Resilience, Security & Cloud Deployment",
      subtitle: "Fault-tolerant fallback chains, 14-minute keep-alive ping, and Port 443 email dispatch",
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full py-2">
          <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-sky-400 font-bold uppercase">
              Multi-Tier Fallbacks
            </div>
            <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
              <li>&bull; <strong>AI Copilot Fallback:</strong> Gemini 1.5 Flash &rarr; Regex Tool Extractor &rarr; Python Math DAG &rarr; Template Sitrep.</li>
              <li>&bull; <strong>Email Dispatch:</strong> Brevo HTTPS REST API v3 (Port 443) &rarr; Resend &rarr; SMTP &rarr; Dev Console.</li>
              <li>&bull; <strong>Unit of Work:</strong> PostgreSQL savepoints prevent partial writes.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold uppercase">
              Cloud Deployment
            </div>
            <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
              <li>&bull; <strong>Frontend:</strong> Next.js 14 on Vercel Edge Network (<code className="text-emerald-300">arthlens-two.vercel.app</code>).</li>
              <li>&bull; <strong>Backend:</strong> FastAPI Docker container on Render (<code className="text-emerald-300">arthlens-n6ah.onrender.com</code>).</li>
              <li>&bull; <strong>14-Minute Ping:</strong> cron-job.org sends automated GET pings preventing container sleep.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/30 bg-[#131b2a] shadow-xl space-y-2">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase">
              Security Perimeter
            </div>
            <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
              <li>&bull; <strong>Cryptographic Tokens:</strong> JWT Bearer tokens with sliding-window refresh rotation.</li>
              <li>&bull; <strong>Argon2id Hashing:</strong> State-of-the-art password protection.</li>
              <li>&bull; <strong>Tenant IDOR Isolation:</strong> Every DB query is scoped by tenant UUID; 403 Forbidden on tamper.</li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 15: Conclusion & Academic Summary
    {
      id: 15,
      category: "Academic Handover",
      title: "Academic Summary, Verification & Repository Artifacts",
      subtitle: "Proven mathematical correctness, enterprise test coverage, and formal OOM compliance",
      render: () => (
        <div className="flex flex-col h-full justify-between py-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-[#131b2a] shadow-xl space-y-2">
              <div className="text-xs font-mono text-emerald-400 font-bold uppercase flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Empirical Test Suite Audit</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
                <li>&bull; <strong>164 Backend Pytest Tests:</strong> 100% passed (Units, contracts, ledger balances).</li>
                <li>&bull; <strong>22 Frontend Vitest Tests:</strong> 100% passed (UI components, money formatting).</li>
                <li>&bull; <strong>8 / 8 Playwright E2E Journeys:</strong> Verified end-to-end user workflows.</li>
                <li>&bull; <strong>Full OOM Rigor:</strong> 23 GoF patterns, SOLID, encapsulation, and pure domain layer.</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl border border-sky-500/30 bg-[#131b2a] shadow-xl space-y-2">
              <div className="text-xs font-mono text-sky-400 font-bold uppercase flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                <span>Repository &amp; Live Links</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 leading-relaxed">
                <li>&bull; <strong>GitHub Repository:</strong> <code className="text-sky-300 font-mono">github.com/ayush-mg/arthlens</code></li>
                <li>&bull; <strong>Formal UML Diagrams:</strong> Class, Use-Case, Sequence &amp; State diagrams in repo.</li>
                <li>&bull; <strong>Live Web App:</strong> <a href="https://arthlens-two.vercel.app" target="_blank" rel="noreferrer" className="text-sky-400 underline">arthlens-two.vercel.app</a></li>
                <li>&bull; <strong>Production API:</strong> <a href="https://arthlens-n6ah.onrender.com" target="_blank" rel="noreferrer" className="text-sky-400 underline">arthlens-n6ah.onrender.com</a></li>
              </ul>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-950/20 text-center">
            <div className="text-xs font-mono text-amber-400 font-bold uppercase tracking-wider mb-1">
              IIIT ALLAHABAD &bull; OBJECT ORIENTED METHODOLOGIES &bull; COURSE PROJECT 2026
            </div>
            <div className="text-sm font-serif font-bold text-slate-100">
              Submitted by: AYUSH MISHRA (IIT2025108) &bull; ABHAY PRATAP SINGH (IIT2025109) &bull; MAYANK PURI (IIT2025104)
            </div>
            <div className="text-xs font-serif italic text-amber-300/80 mt-1">
              &quot;अर्थLens — Know the numbers. Move with intent.&quot;
            </div>
          </div>
        </div>
      ),
    },
  ];

  useEffect(() => {
    // Force dark background on html and body for presentation deck
    const prevHtmlBg = document.documentElement.style.backgroundColor;
    const prevBodyBg = document.body.style.backgroundColor;
    document.documentElement.style.backgroundColor = "#080b12";
    document.body.style.backgroundColor = "#080b12";
    return () => {
      document.documentElement.style.backgroundColor = prevHtmlBg;
      document.body.style.backgroundColor = prevBodyBg;
    };
  }, []);

  const slide = slides[currentSlide];

  return (
    <div className="fixed inset-0 z-50 w-screen h-screen bg-[#080b12] text-slate-100 flex flex-col font-sans select-none overflow-hidden">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-slate-800 bg-[#080b12] px-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-gradient-to-tr from-sky-500 to-emerald-400 flex items-center justify-center font-bold text-slate-950 text-xs">
            AL
          </div>
          <div>
            <div className="text-xs font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <span>अर्थLens (ArthLens)</span>
              <span className="text-slate-500 font-mono">/</span>
              <span className="text-sky-400 font-mono text-[11px]">OOM PROJECT REPORT</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono">
              IIIT ALLAHABAD &bull; IIT2025108, IIT2025109, IIT2025104
            </div>
          </div>
        </div>

        {/* Slide Counter & Controls */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-1.5 text-xs font-mono text-slate-400">
            <span>SLIDE</span>
            <span className="text-sky-400 font-bold text-sm">{String(currentSlide + 1).padStart(2, "0")}</span>
            <span>/</span>
            <span>{String(totalSlides).padStart(2, "0")}</span>
          </div>

          <div className="h-4 w-px bg-slate-800 hidden md:block" />

          <button
            onClick={() => setIsAutoplay(!isAutoplay)}
            className={`p-1.5 rounded text-xs flex items-center gap-1 border transition-colors ${
              isAutoplay
                ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
            }`}
            title="Toggle Autoplay (12s per slide)"
          >
            {isAutoplay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline text-[11px] font-mono">{isAutoplay ? "PAUSE" : "AUTO"}</span>
          </button>

          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded text-xs bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200 transition-colors"
            title="Toggle Fullscreen (F)"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </header>

      {/* Slide Progress Bar */}
      <div className="w-full bg-slate-900 h-1">
        <motion.div
          className="h-full bg-gradient-to-r from-sky-500 via-emerald-400 to-amber-400"
          initial={{ width: 0 }}
          animate={{ width: `${((currentSlide + 1) / totalSlides) * 100}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Main Slide Presentation Stage */}
      <main className="flex-1 relative flex items-center justify-center p-4 md:p-8 overflow-hidden bg-[#080b12]">
        <div className="w-full max-w-6xl h-full max-h-[820px] flex flex-col justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentSlide}
              initial={{ opacity: 0, x: 25, scale: 0.98 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -25, scale: 0.98 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="w-full h-full flex flex-col justify-between"
            >
              {/* Slide Title Bar */}
              {slide.id !== 1 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 text-xs font-mono text-sky-400 uppercase tracking-widest">
                    <span>{slide.category}</span>
                  </div>
                  <h2 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight font-serif mt-1">
                    {slide.title}
                  </h2>
                  {slide.subtitle && (
                    <p className="text-xs md:text-sm text-slate-400 mt-1 max-w-4xl">
                      {slide.subtitle}
                    </p>
                  )}
                </div>
              )}

              {/* Slide Content */}
              <div className="flex-1 flex flex-col justify-center">
                {slide.render()}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Bottom Navigation Dock */}
      <footer className="h-16 border-t border-slate-800/80 bg-[#0b101b] border border-slate-700/60 backdrop-blur-md px-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-2">
          <button
            onClick={prevSlide}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-200 text-xs font-mono hover:bg-slate-800 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden sm:inline">PREV</span>
          </button>
          <button
            onClick={nextSlide}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-sky-500/40 bg-sky-500/10 text-sky-300 text-xs font-mono hover:bg-sky-500/20 transition-colors"
          >
            <span className="hidden sm:inline">NEXT</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Thumbnail Slide Dots / Numbers */}
        <div className="hidden lg:flex items-center gap-1.5">
          {slides.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => setCurrentSlide(idx)}
              className={`w-7 h-7 rounded text-[11px] font-mono transition-all ${
                currentSlide === idx
                  ? "bg-sky-500 text-slate-950 font-bold scale-110 shadow-lg shadow-sky-500/30"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
              title={`Slide ${idx + 1}: ${s.title}`}
            >
              {idx + 1}
            </button>
          ))}
        </div>

        {/* Keyboard Hint */}
        <div className="text-[11px] font-mono text-slate-500 hidden sm:block">
          Navigate: <kbd className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">&larr;</kbd> <kbd className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">&rarr;</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">Space</kbd>
        </div>
      </footer>
    </div>
  );
}
