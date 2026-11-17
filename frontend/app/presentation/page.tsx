"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  ArrowLeft,
  Maximize2,
  Minimize2,
  Play,
  Pause,
  ExternalLink,
  CheckCircle2
} from "lucide-react";

export default function PresentationPage() {
  const [currentSlide, setCurrentSlide] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAutoplay, setIsAutoplay] = useState(false);

  const nextSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev < 15 ? prev + 1 : 1));
  }, []);

  const prevSlide = useCallback(() => {
    setCurrentSlide((prev) => (prev > 1 ? prev - 1 : 15));
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        nextSlide();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prevSlide();
      } else if (e.key.toLowerCase() === "f") {
        toggleFullscreen();
      } else if (e.key >= "1" && e.key <= "9") {
        setCurrentSlide(parseInt(e.key));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [nextSlide, prevSlide]);

  useEffect(() => {
    if (!isAutoplay) return;
    const interval = setInterval(nextSlide, 10000);
    return () => clearInterval(interval);
  }, [isAutoplay, nextSlide]);

  useEffect(() => {
    const origHtmlBg = document.documentElement.style.backgroundColor;
    const origBodyBg = document.body.style.backgroundColor;
    document.documentElement.style.backgroundColor = "#FAF7F2";
    document.body.style.backgroundColor = "#FAF7F2";
    return () => {
      document.documentElement.style.backgroundColor = origHtmlBg;
      document.body.style.backgroundColor = origBodyBg;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 w-screen h-screen bg-[#FAF7F2] text-[#231412] flex flex-col font-sans select-none overflow-hidden">
      {/* Top Thin Red Accent Strip */}
      <div className="h-1.5 w-full bg-[#C8281E] shrink-0" />

      {/* Header Bar */}
      <header className="h-12 border-b border-[#231412]/15 px-6 flex items-center justify-between text-xs shrink-0 bg-[#FAF7F2]">
        <div className="flex items-center space-x-3">
          <Link
            href="/"
            className="flex items-center space-x-1.5 font-bold tracking-wider hover:text-[#C8281E] transition-colors"
          >
            <span>अर्थLENS</span>
            <span className="text-[#231412]/40">/</span>
            <span>ARTHLENS</span>
          </Link>
          <span className="text-[#231412]/30">|</span>
          <span className="font-mono text-[11px] font-bold text-[#C8281E]">
            {currentSlide === 1
              ? "COURSE PROJECT PRESENTATION"
              : currentSlide === 2
              ? "01 / PROBLEM"
              : currentSlide === 3
              ? "02 / PRODUCT"
              : currentSlide === 4
              ? "03 / FEATURES"
              : currentSlide === 5
              ? "04 / ENGINEERING"
              : currentSlide === 6
              ? "05 / OBJECT MODELING"
              : currentSlide === 7
              ? "06 / OOM CONCEPTS"
              : currentSlide === 8
              ? "07 / DOMAIN RELATIONSHIPS"
              : currentSlide === 9
              ? "08 / CORE WORKFLOW"
              : currentSlide === 10
              ? "09 / FINANCIAL INTELLIGENCE"
              : currentSlide === 11
              ? "10 / HUMAN-IN-THE-LOOP"
              : currentSlide === 12
              ? "11 / SOFTWARE DESIGN"
              : currentSlide === 13
              ? "12 / DESIGN PATTERNS"
              : currentSlide === 14
              ? "13 / VERIFICATION"
              : "ARTHLENS / OBJECT-ORIENTED METHODOLOGY"}
          </span>
        </div>

        {/* Jump Numbers */}
        <div className="hidden lg:flex items-center space-x-1">
          {Array.from({ length: 15 }, (_, i) => i + 1).map((num) => (
            <button
              key={num}
              onClick={() => setCurrentSlide(num)}
              className={`w-5 h-5 text-[10px] font-mono font-bold transition-all border ${
                currentSlide === num
                  ? "bg-[#C8281E] text-white border-[#C8281E]"
                  : "bg-white text-[#231412]/60 border-[#231412]/15 hover:border-[#C8281E]"
              }`}
            >
              {num}
            </button>
          ))}
        </div>

        {/* Navigation & Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsAutoplay(!isAutoplay)}
            className="p-1 border border-[#231412]/20 bg-white hover:text-[#C8281E]"
            title="Toggle Autoplay"
          >
            {isAutoplay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1 border border-[#231412]/20 bg-white hover:text-[#C8281E]"
            title="Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <span className="font-mono text-xs font-bold text-[#C8281E]">
            {String(currentSlide).padStart(2, "0")} / 15
          </span>
        </div>
      </header>

      {/* Main Slide Body */}
      <main className="flex-1 relative overflow-hidden p-6 md:p-8 flex flex-col justify-between max-w-7xl mx-auto w-full">
        <AnimatePresence mode="wait">
          {/* SLIDE 1 */}
          {currentSlide === 1 && (
            <motion.div
              key="s1"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"
            >
              <div className="lg:col-span-7 space-y-4">
                <div className="text-xs font-mono font-bold tracking-widest text-[#231412]/80 uppercase">
                  INDIAN INSTITUTE OF INFORMATION TECHNOLOGY ALLAHABAD (IIITA)
                </div>
                <h1 className="text-5xl md:text-6xl font-black tracking-tight text-[#231412]">
                  ARTH<span className="text-[#C8281E]">LENS</span>
                </h1>
                <h2 className="text-2xl font-bold text-[#231412]">
                  A Sovereign Financial Operating System
                </h2>
                <p className="text-sm text-[#5C403B] leading-relaxed max-w-xl">
                  Evidence-driven financial operations, deterministic integer-paisa Khata, and staged AI decision intelligence for Indian MSMEs.
                </p>

                <div className="pt-2">
                  <div className="inline-block px-3 py-1 bg-[#FAF7F2] border border-[#231412]/20 text-[11px] font-mono font-bold uppercase text-[#231412]/80">
                    OBJECT-ORIENTED METHODOLOGY • PROJECT PRESENTATION
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between max-w-md p-2 bg-white border border-[#231412]/15">
                    <span className="text-xs font-bold text-[#231412]">Abhay Pratap Singh</span>
                    <span className="text-xs font-mono font-bold text-[#C8281E]">IIT2025109</span>
                  </div>
                  <div className="flex items-center justify-between max-w-md p-2 bg-white border border-[#231412]/15">
                    <span className="text-xs font-bold text-[#231412]">Ayush Mishra</span>
                    <span className="text-xs font-mono font-bold text-[#C8281E]">IIT2025108</span>
                  </div>
                  <div className="flex items-center justify-between max-w-md p-2 bg-white border border-[#231412]/15">
                    <span className="text-xs font-bold text-[#231412]">Mayank Puri</span>
                    <span className="text-xs font-mono font-bold text-[#C8281E]">IIT2025104</span>
                  </div>
                </div>
              </div>

              {/* Right Side UI Mockup Widget */}
              <div className="lg:col-span-5 flex flex-col items-center">
                <div className="w-full max-w-md bg-white border border-[#231412]/20 shadow-md p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#231412]/10 pb-2">
                    <span className="text-[10px] font-mono font-bold text-[#C8281E] tracking-wider uppercase">
                      ARTHLENS / OVERVIEW
                    </span>
                    <span className="text-[10px] tracking-widest text-[#231412]/40">● ● ●</span>
                  </div>

                  <div className="text-xs font-bold text-[#231412]">Sovereign financial pulse, at a glance</div>

                  {/* Simulated Tabs */}
                  <div className="flex space-x-1 text-[11px] font-mono">
                    <span className="px-2.5 py-1 bg-[#231412] text-white font-bold">Overview</span>
                    <span className="px-2.5 py-1 bg-[#FAF7F2] border border-[#231412]/15 text-[#5C403B]">Khata</span>
                    <span className="px-2.5 py-1 bg-[#FAF7F2] border border-[#231412]/15 text-[#5C403B]">Inventory</span>
                  </div>

                  {/* 2 Metric Tiles */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-[#FAF7F2] border border-[#231412]/10 space-y-1">
                      <div className="text-[9px] font-mono text-[#5C403B] uppercase">INVOICE VALUE</div>
                      <div className="text-xl font-black text-[#231412]">₹1.18L</div>
                      <div className="text-[9px] font-mono text-[#2D7D52]">Paisa-exact (11800000)</div>
                    </div>
                    <div className="p-3 bg-[#FAF7F2] border border-[#231412]/10 space-y-1">
                      <div className="text-[9px] font-mono text-[#5C403B] uppercase">GST RATE</div>
                      <div className="text-xl font-black text-[#231412]">18%</div>
                      <div className="text-[9px] font-mono text-[#C8281E]">CGST 9% + SGST 9%</div>
                    </div>
                  </div>

                  {/* Business Pulse Bar Graph */}
                  <div className="p-3 bg-[#FAF7F2] border border-[#231412]/10 space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-mono">
                      <span className="font-bold text-[#231412]">Business pulse</span>
                      <span className="text-[#2D7D52] font-bold">0.00ms Drift • 100% Deterministic</span>
                    </div>
                    <div className="flex items-end space-x-1.5 h-12 pt-2">
                      <div className="flex-1 bg-[#231412]/20 h-6" />
                      <div className="flex-1 bg-[#231412]/30 h-9" />
                      <div className="flex-1 bg-[#231412]/40 h-7" />
                      <div className="flex-1 bg-[#C8281E]/60 h-11" />
                      <div className="flex-1 bg-[#231412]/50 h-8" />
                      <div className="flex-1 bg-[#2D7D52]/80 h-12" />
                      <div className="flex-1 bg-[#231412]/60 h-10" />
                      <div className="flex-1 bg-[#C8281E] h-12" />
                    </div>
                  </div>

                  <div className="text-[9px] font-mono text-center text-[#9A7E78]">
                    UI-INSPIRED VISUAL • SOVEREIGN FINANCIAL TOPOLOGY
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 2: 01 / PROBLEM */}
          {currentSlide === 2 && (
            <motion.div
              key="s2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  WHY WE BUILT IT
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Small businesses, complex numbers.</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Disconnected tools create operational chaos, floating-point drift, and unmonitored financial risk.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#C8281E] space-y-2">
                  <div className="text-2xl font-black font-mono text-[#C8281E]">01</div>
                  <h3 className="text-base font-bold text-[#231412]">Fragmented records</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Siloed billing, purchases, stock, and Khata balances create severe information asymmetry. Over ₹35L+ trapped in overdue receivables without aging bucket visibility.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#D4A359] space-y-2">
                  <div className="text-2xl font-black font-mono text-[#D4A359]">02</div>
                  <h3 className="text-base font-bold text-[#231412]">Financial drift</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    IEEE 754 floating-point errors compound across ledgers. Weighted-average costing conceals true unit gross margin loss under supplier inflation.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#C8281E] space-y-2">
                  <div className="text-2xl font-black font-mono text-[#C8281E]">03</div>
                  <h3 className="text-base font-bold text-[#231412]">Unsafe automation</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Autonomous LLMs executing direct SQL updates or disbursements risk catastrophic ledger corruption. Financial actions require mathematical proof and human approval gates.
                  </p>
                </div>
              </div>

              <div className="p-3 bg-[#F3ECE3] border border-[#231412]/20 flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-[#C8281E]">ARTHLENS IDEA</span>
                <span className="text-[#231412] font-semibold">One connected system. Verified integer-paisa mathematics. Human-governed control.</span>
              </div>
            </motion.div>
          )}

          {/* SLIDE 3: 02 / PRODUCT */}
          {currentSlide === 3 && (
            <motion.div
              key="s3"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  THE SOLUTION
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Meet ArthLens</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  A workspace for day-to-day operations, double-entry Khata, and evidence-backed decisions.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                {/* Left Simulated App Card */}
                <div className="lg:col-span-6 bg-white border border-[#231412]/20 p-5 shadow-sm space-y-3">
                  <div className="flex justify-between items-center border-b border-[#231412]/10 pb-2">
                    <span className="font-bold text-xs text-[#231412]">अर्थLens Overview</span>
                    <span className="text-[10px] font-mono text-[#C8281E]">LIVE SYSTEM</span>
                  </div>
                  <div className="text-[11px] font-mono text-[#5C403B]">CORE OPERATING INDICATORS (PAISA-EXACT)</div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-[#FAF7F2] border border-[#231412]/10">
                      <div className="text-[9px] font-mono text-[#5C403B]">SALES</div>
                      <div className="text-sm font-black text-[#231412]">₹1.18L</div>
                      <div className="text-[8px] font-mono text-[#2D7D52]">Paisa-exact</div>
                    </div>
                    <div className="p-2 bg-[#FAF7F2] border border-[#231412]/10">
                      <div className="text-[9px] font-mono text-[#5C403B]">UNITS SOLD</div>
                      <div className="text-sm font-black text-[#231412]">20</div>
                      <div className="text-[8px] font-mono text-[#C8281E]">FIFO Batch</div>
                    </div>
                    <div className="p-2 bg-[#FAF7F2] border border-[#231412]/10">
                      <div className="text-[9px] font-mono text-[#5C403B]">GST RATE</div>
                      <div className="text-sm font-black text-[#231412]">18%</div>
                      <div className="text-[8px] font-mono text-[#D4A359]">Compliant</div>
                    </div>
                  </div>

                  <div className="p-2.5 bg-[#F3ECE3] border border-[#231412]/15 text-center space-y-1">
                    <div className="text-xs font-bold text-[#231412]">Cash & receivables: Ledgers stay in sync</div>
                    <div className="text-[11px] font-mono font-bold text-[#2D7D52]">
                      DEBIT = CREDIT: Σ Debits ≡ Σ Credits (Zero Drift)
                    </div>
                  </div>
                </div>

                {/* Right 3 Pillars */}
                <div className="lg:col-span-6 flex flex-col justify-between space-y-3">
                  <div className="p-3.5 bg-white border border-[#231412]/15 shadow-sm border-l-4 border-l-[#C8281E]">
                    <div className="text-[10px] font-mono font-bold text-[#C8281E]">01 OPERATE</div>
                    <div className="text-xs font-semibold text-[#231412] mt-0.5">
                      Sales invoicing · purchase bills · perpetual FIFO inventory batch allocation
                    </div>
                  </div>
                  <div className="p-3.5 bg-white border border-[#231412]/15 shadow-sm border-l-4 border-l-[#2D7D52]">
                    <div className="text-[10px] font-mono font-bold text-[#2D7D52]">02 UNDERSTAND</div>
                    <div className="text-xs font-semibold text-[#231412] mt-0.5">
                      Double-entry Khata · dynamic financial statements · DuPont profitability ratios
                    </div>
                  </div>
                  <div className="p-3.5 bg-white border border-[#231412]/15 shadow-sm border-l-4 border-l-[#D4A359]">
                    <div className="text-[10px] font-mono font-bold text-[#D4A359]">03 DECIDE</div>
                    <div className="text-xs font-semibold text-[#231412] mt-0.5">
                      What-If scenario laboratory · staged AI copilot · immutable audit trail
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 4: 03 / FEATURES */}
          {currentSlide === 4 && (
            <motion.div
              key="s4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  COVERAGE
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">18 chapters. One business workspace.</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  18 bounded contexts organized into six practical capability groups.
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">01 COMMERCIAL</div>
                  <div className="text-xs font-semibold text-[#231412]">Sales (B2B/B2C, HSN) / Purchases (Inward bills) / Inventory (Perpetual FIFO batches)</div>
                </div>
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">02 FINANCE</div>
                  <div className="text-xs font-semibold text-[#231412]">Khata (Double-entry ledgers) / Finance (Treasury bridge) / Analytics (DuPont ROE)</div>
                </div>
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#D4A359]">03 PLANNING</div>
                  <div className="text-xs font-semibold text-[#231412]">Decisions (Capital appraisal) / Scenarios (What-If stress test) / Goals (Runway milestones)</div>
                </div>
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">04 INTELLIGENCE</div>
                  <div className="text-xs font-semibold text-[#231412]">AI Agent (Read-only tool DAG) / Reports (P&L, Balance Sheet) / Constellation (Node graph)</div>
                </div>
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">05 RELATIONSHIPS</div>
                  <div className="text-xs font-semibold text-[#231412]">Customers (Credit aging buckets) / Suppliers (AP schedules) / Members (Role RBAC)</div>
                </div>
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#231412] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#231412]">06 GOVERNANCE</div>
                  <div className="text-xs font-semibold text-[#231412]">Overview (Operational pulse) / Audit & Access (SHA-256 logs) / Settings (Tenant isolation)</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 5: 04 / ENGINEERING */}
          {currentSlide === 5 && (
            <motion.div
              key="s5"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  TECH STACK
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Designed as a layered application</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Presentation, domain behavior, and persistence each have a distinct responsibility under Clean Architecture.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#C8281E] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#C8281E]">01 FRONTEND</div>
                  <h3 className="text-base font-bold text-[#231412]">Next.js 14 · TypeScript</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    18-chapter workspace, role-aware reactive components, Framer Motion transitions, zero-radius design tokens.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#2D7D52] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#2D7D52]">02 BACKEND</div>
                  <h3 className="text-base font-bold text-[#231412]">Python · FastAPI</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Coordinates transactional use-cases, perpetual FIFO lot engine, staged AI governance, and REST endpoints.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#D4A359] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#D4A359]">03 DATA</div>
                  <h3 className="text-base font-bold text-[#231412]">PostgreSQL 16 · SQLAlchemy</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Stores immutable double-entry journal vouchers, FIFO stock lot movements, and cryptographically sealed audit records.
                  </p>
                </div>
              </div>

              <div className="p-3 bg-[#F3ECE3] border border-[#231412]/15 text-center text-xs font-mono font-bold text-[#231412]">
                HTTPS / JSON REST API • JWT + Tenant-Scoping RBAC • ACID Atomic Database Transactions
              </div>
            </motion.div>
          )}

          {/* SLIDE 6: 05 / OBJECT MODELING */}
          {currentSlide === 6 && (
            <motion.div
              key="s6"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  CLASSES & OBJECTS
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Domain model: money you can trust</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Object state and business invariants belong together in pure immutable domain entities.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                <div className="lg:col-span-7 bg-[#231412] text-white p-4 font-mono text-xs shadow-md border-l-4 border-l-[#C8281E]">
                  <div className="text-[#9A7E78] mb-2">{"// backend/arthlens/domain/models.py"}</div>
                  <pre className="text-xs leading-relaxed overflow-x-auto text-[#FAF7F2]">
{`@dataclass(frozen=True)
class Money:
    paise: int  # exact integer scaling (10^2)
    currency: str = "INR"

    def __post_init__(self):
        if not isinstance(self.paise, int) or self.paise < 0:
            raise InvalidMoneyException("Must be non-negative integer paise")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchException()
        return Money(self.paise + other.paise, self.currency)`}
                  </pre>
                </div>

                <div className="lg:col-span-5 grid grid-cols-1 gap-2.5">
                  <div className="p-2.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E]">
                    <div className="text-[10px] font-mono font-bold text-[#C8281E]">ATTRIBUTES</div>
                    <div className="text-xs text-[#231412]">paise: int (10^2 scale) • currency: str (ISO-4217)</div>
                  </div>
                  <div className="p-2.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52]">
                    <div className="text-[10px] font-mono font-bold text-[#2D7D52]">CONSTRUCTOR</div>
                    <div className="text-xs text-[#231412]">__init__ + validation in __post_init__ rejecting floats or negatives</div>
                  </div>
                  <div className="p-2.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359]">
                    <div className="text-[10px] font-mono font-bold text-[#D4A359]">ENCAPSULATION</div>
                    <div className="text-xs text-[#231412]">Frozen immutable value object; exact arithmetic rules without drift</div>
                  </div>
                  <div className="p-2.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#231412]">
                    <div className="text-[10px] font-mono font-bold text-[#231412]">BEHAVIOR</div>
                    <div className="text-xs text-[#231412]">zero(), from_rupees(), __add__(), __sub__(), __mul__()</div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 7: 06 / OOM CONCEPTS */}
          {currentSlide === 7 && (
            <motion.div
              key="s7"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  OBJECT ORIENTATION
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">The four OOP pillars in real code</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Examples drawn directly from ArthLens domain aggregates, repository ports, and decision modules.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#C8281E] space-y-1.5">
                  <div className="text-xs font-mono font-bold text-[#C8281E]">01 Encapsulation</div>
                  <h3 className="text-sm font-bold text-[#231412]">SalesInvoice.recalculate_totals()</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Private line collections and tax totals. Mutated only through guarded domain methods; locked permanently once issued.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#2D7D52] space-y-1.5">
                  <div className="text-xs font-mono font-bold text-[#2D7D52]">02 Abstraction</div>
                  <h3 className="text-sm font-bold text-[#231412]">AbstractSalesInvoiceRepository</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Application services interact with get_by_id() and save() contracts, completely decoupled from PostgreSQL/SQLAlchemy.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#D4A359] space-y-1.5">
                  <div className="text-xs font-mono font-bold text-[#D4A359]">03 Inheritance</div>
                  <h3 className="text-sm font-bold text-[#231412]">InsufficientStockException</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Specialized domain exception inheriting from DomainException, enabling unified error handling across services.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#231412] space-y-1.5">
                  <div className="text-xs font-mono font-bold text-[#231412]">04 Polymorphism</div>
                  <h3 className="text-sm font-bold text-[#231412]">CapitalDecisionStrategy.evaluate()</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Machine-purchase and expansion strategies provide polymorphic evaluations; dynamic polymorphic GST tax dispatch.
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 8: 07 / DOMAIN RELATIONSHIPS */}
          {currentSlide === 8 && (
            <motion.div
              key="s8"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  OBJECT RELATIONSHIPS
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">How business objects work together</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  OOM relationships reflect ownership, reuse, and identity—not just physical foreign keys.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#C8281E] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#C8281E]">COMPOSITION (◆)</div>
                  <h3 className="text-sm font-bold text-[#231412]">SalesInvoice owns SalesInvoiceItem</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Line items have no independent existence outside the invoice; deleting cascades lifecycle destruction.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#2D7D52] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#2D7D52]">AGGREGATION (◇)</div>
                  <h3 className="text-sm font-bold text-[#231412]">BusinessWorkspace groups BusinessMembership</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    Members belong to an enterprise workspace while underlying user accounts and audit records remain independent.
                  </p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-5 shadow-sm border-l-4 border-l-[#D4A359] space-y-2">
                  <div className="text-xs font-mono font-bold text-[#D4A359]">ASSOCIATION (→)</div>
                  <h3 className="text-sm font-bold text-[#231412]">SalesInvoice references Customer</h3>
                  <p className="text-xs text-[#5C403B] leading-relaxed">
                    An invoice links to a customer via customer_id, preserving permanent ledger history even if customer records change.
                  </p>
                </div>
              </div>

              <div className="p-3 bg-[#F3ECE3] border border-[#231412]/15 text-center text-xs font-mono text-[#5C403B]">
                Modeling benefit: Clear lifecycle boundaries prevent orphan records, eliminate memory leaks, and guarantee ledger immutability.
              </div>
            </motion.div>
          )}

          {/* SLIDE 9: 08 / CORE WORKFLOW */}
          {currentSlide === 9 && (
            <motion.div
              key="s9"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  A REAL BUSINESS SCENARIO
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">One invoice, four synchronized outcomes</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Illustrative order-to-ledger execution demonstrating the atomic Unit of Work pattern.
                </p>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">01 INVOICE ISSUED</div>
                  <div className="text-lg font-black text-[#231412]">₹1,00,000</div>
                  <div className="text-xs text-[#5C403B]">20 units × ₹5,000 unit price. Customer credit limit & GSTIN validated.</div>
                </div>

                <div className="p-4 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#D4A359]">02 GST CALCULATED</div>
                  <div className="text-lg font-black text-[#231412]">₹18,000</div>
                  <div className="text-xs text-[#5C403B]">18% statutory tax recorded (9% CGST ₹9,000 + 9% SGST ₹9,000). Total: ₹1.18L.</div>
                </div>

                <div className="p-4 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">03 FIFO STOCK USED</div>
                  <div className="text-lg font-black text-[#231412]">₹64,000</div>
                  <div className="text-xs text-[#5C403B]">20 units × ₹3,200 batch acquisition cost (Realized Gross Margin: ₹36,000).</div>
                </div>

                <div className="p-4 bg-white border border-[#231412]/15 border-l-4 border-l-[#231412] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#231412]">04 KHATA POSTED</div>
                  <div className="text-lg font-black text-[#231412]">₹1,18,000</div>
                  <div className="text-xs text-[#5C403B]">Customer receivable debited ₹1.18L; Revenue credited ₹1.00L; Output tax credited ₹18K.</div>
                </div>
              </div>

              <div className="p-3 bg-[#F3ECE3] border border-[#231412]/15 text-center text-xs font-mono font-bold text-[#C8281E]">
                ONE ATOMIC TRANSACTION: Invoice + Inventory + Khata either all commit together—or all roll back (Zero Drift Guarantee).
              </div>
            </motion.div>
          )}

          {/* SLIDE 10: 09 / FINANCIAL INTELLIGENCE */}
          {currentSlide === 10 && (
            <motion.div
              key="s10"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  DETERMINISTIC DECISION-MAKING
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Insights backed by mathematical rules</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  The deterministic financial engine computes verified evidence; the AI layer explains and stages actions.
                </p>
              </div>

              <div className="p-3 bg-[#F3ECE3] border border-[#C8281E]/30 text-center space-y-1">
                <div className="text-[10px] font-mono font-bold text-[#C8281E] uppercase">THE NON-NEGOTIABLE RULE</div>
                <div className="text-base font-black font-mono text-[#231412]">Σ Debits = Σ Credits</div>
                <div className="text-xs font-mono text-[#5C403B]">Exact-paisa ledger reconciliation enforced on every journal entry</div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-[#231412]/15 p-4 shadow-sm border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">LIQUIDITY</div>
                  <h3 className="text-sm font-bold text-[#231412]">Current ratio • Quick ratio • 90-day cashflow runway</h3>
                  <p className="text-xs text-[#5C403B]">Traces liquid reserves, overdue receivables velocity, and near-term ability to pay.</p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-4 shadow-sm border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">PROFITABILITY</div>
                  <h3 className="text-sm font-bold text-[#231412]">Gross margin proof • FIFO COGS • DuPont ROE</h3>
                  <p className="text-xs text-[#5C403B]">3-tier DuPont decomposition: Net Margin × Asset Turnover × Financial Leverage.</p>
                </div>

                <div className="bg-white border border-[#231412]/15 p-4 shadow-sm border-l-4 border-l-[#D4A359] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#D4A359]">PLANNING</div>
                  <h3 className="text-sm font-bold text-[#231412]">Real NPV • CAGR • What-If Stress Testing</h3>
                  <p className="text-xs text-[#5C403B]">Simulate inflation shocks, supplier delays, and investment choices with explicit assumptions.</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 11: 10 / HUMAN-IN-THE-LOOP */}
          {currentSlide === 11 && (
            <motion.div
              key="s11"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  AI WITH GUARDRAILS
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">The copilot proposes. A human approves.</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  AI can analyze and stage an action; it cannot silently modify financial records or mutate ledgers.
                </p>
              </div>

              {/* Staged Copilot Interaction Box */}
              <div className="max-w-2xl mx-auto w-full bg-white border border-[#231412]/20 shadow-md p-5 space-y-3">
                <div className="flex justify-between items-center border-b border-[#231412]/10 pb-2">
                  <span className="text-[10px] font-mono font-bold text-[#C8281E] uppercase">ARTHLENS / FINANCIAL COPILOT</span>
                  <span className="text-[10px] font-mono text-[#2D7D52] font-bold">READ-ONLY DAG TOOL</span>
                </div>

                <div>
                  <div className="text-[10px] font-mono text-[#5C403B] uppercase">OWNER QUESTION</div>
                  <div className="text-sm font-bold text-[#231412]">Should we finance a new packaging machine?</div>
                </div>

                <div className="p-3 bg-[#FAF7F2] border border-[#231412]/10 space-y-1">
                  <div className="text-[10px] font-mono text-[#5C403B] uppercase">EVIDENCE-BACKED RESPONSE</div>
                  <div className="text-xs text-[#231412]">
                    Verified tool DAGs calculate NPV (+₹2.4L), cash runway (-1.2 mo), and debt coverage. A proposed action is staged for review.
                  </div>
                </div>

                <div className="p-3 bg-[#F3ECE3] border border-[#C8281E]/30 space-y-2">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E] uppercase">PENDING CONFIRMATION</div>
                  <div className="grid grid-cols-3 gap-2 text-[11px]">
                    <div>
                      <span className="font-bold text-[#231412]">Status:</span>
                      <span className="text-[#5C403B] block">Staged, not executed</span>
                    </div>
                    <div>
                      <span className="font-bold text-[#231412]">Audit:</span>
                      <span className="text-[#5C403B] block">SHA-256 seal logged</span>
                    </div>
                    <div>
                      <span className="font-bold text-[#231412]">Approval:</span>
                      <span className="text-[#5C403B] block">Explicit owner confirm</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-3 pt-1">
                  <button className="px-4 py-1.5 text-xs font-mono font-bold border border-[#231412]/30 bg-white hover:bg-[#FAF7F2]">
                    REVIEW
                  </button>
                  <button className="px-4 py-1.5 text-xs font-mono font-bold bg-[#C8281E] text-white border border-[#C8281E] hover:bg-[#A81E15]">
                    CONFIRM
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 12: 11 / SOFTWARE DESIGN */}
          {currentSlide === 12 && (
            <motion.div
              key="s12"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  SOLID
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Five principles, visible in the implementation</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  Object-oriented design makes ArthLens easier to maintain, test, and safely extend.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-xl font-black font-mono text-[#C8281E]">S</div>
                  <div className="text-xs font-bold text-[#231412]">Single Responsibility</div>
                  <div className="text-[11px] text-[#5C403B]">InventoryCostService owns FIFO lot costing exclusively; InvoiceValidator owns schema and tax validation.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-xl font-black font-mono text-[#2D7D52]">O</div>
                  <div className="text-xs font-bold text-[#231412]">Open / Closed</div>
                  <div className="text-[11px] text-[#5C403B]">BusinessToolRegistry & IScenarioShock accept new tools and stress models without modifying core loops.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359] space-y-1">
                  <div className="text-xl font-black font-mono text-[#D4A359]">L</div>
                  <div className="text-xs font-bold text-[#231412]">Liskov Substitution</div>
                  <div className="text-[11px] text-[#5C403B]">PostgresLedgerRepository and InMemoryLedgerRepository fulfill identical behavioral contracts in test & prod.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#231412] space-y-1">
                  <div className="text-xl font-black font-mono text-[#231412]">I</div>
                  <div className="text-xs font-bold text-[#231412]">Interface Segregation</div>
                  <div className="text-[11px] text-[#5C403B]">Audit (IAuditable), rate-limit, and Khata query contracts are narrow and segregated by client role.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-xl font-black font-mono text-[#C8281E]">D</div>
                  <div className="text-xs font-bold text-[#231412]">Dependency Inversion</div>
                  <div className="text-[11px] text-[#5C403B]">BusinessService receives abstract repository interfaces injected dynamically via FastAPI DI container.</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 13: 12 / DESIGN PATTERNS */}
          {currentSlide === 13 && (
            <motion.div
              key="s13"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  REUSABLE ARCHITECTURE
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Patterns that turn requirements into robust code</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  A curated selection drawn from our documented 23-pattern enterprise architecture catalog.
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">VALUE OBJECT</div>
                  <div className="text-sm font-bold text-[#231412]">Money</div>
                  <div className="text-xs text-[#5C403B]">Validated, immutable monetary state with integer-paisa scaling and operator overloading.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">REPOSITORY</div>
                  <div className="text-sm font-bold text-[#231412]">Invoice repositories</div>
                  <div className="text-xs text-[#5C403B]">Clean separation of business domain logic from SQL/PostgreSQL persistence mechanics.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#D4A359]">UNIT OF WORK</div>
                  <div className="text-sm font-bold text-[#231412]">BusinessService</div>
                  <div className="text-xs text-[#5C403B]">Atomic multi-table transactions guaranteeing all-or-nothing execution across domains.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">STRATEGY</div>
                  <div className="text-sm font-bold text-[#231412]">CapitalDecisionStrategy</div>
                  <div className="text-xs text-[#5C403B]">Replaceable evaluation algorithms for ROI, debt capacity, and capital appraisal.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">FACTORY METHOD</div>
                  <div className="text-sm font-bold text-[#231412]">Money.zero() & VoucherFactory</div>
                  <div className="text-xs text-[#5C403B]">Consistent, validated domain object creation enforcing type invariants.</div>
                </div>

                <div className="p-3.5 bg-white border border-[#231412]/15 border-l-4 border-l-[#231412] space-y-1">
                  <div className="text-[10px] font-mono font-bold text-[#231412]">REGISTRY</div>
                  <div className="text-sm font-bold text-[#231412]">BusinessToolRegistry</div>
                  <div className="text-xs text-[#5C403B]">Extensible, verified tool dispatch providing safe, read-only tools to the AI copilot.</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 14: 13 / VERIFICATION */}
          {currentSlide === 14 && (
            <motion.div
              key="s14"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="inline-block px-2.5 py-0.5 bg-[#C8281E] text-white text-[10px] font-mono font-bold uppercase mb-2">
                  TESTING & RESILIENCE
                </div>
                <h1 className="text-3xl font-extrabold text-[#231412]">Confidence is designed into the system</h1>
                <p className="text-sm text-[#5C403B] mt-1">
                  194 automated test suites verify mathematical precision, security boundaries, and multi-tenant isolation.
                </p>
              </div>

              {/* 3 Metric Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="p-5 bg-white border border-[#231412]/15 shadow-sm text-center space-y-1 border-t-4 border-t-[#2D7D52]">
                  <div className="text-xs font-mono font-bold text-[#5C403B] uppercase">BACKEND TESTS</div>
                  <div className="text-4xl font-black text-[#2D7D52]">164</div>
                  <div className="text-xs text-[#5C403B]">Pytest unit, contract, FIFO lot queue & IDOR security (100% green)</div>
                </div>

                <div className="p-5 bg-white border border-[#231412]/15 shadow-sm text-center space-y-1 border-t-4 border-t-[#C8281E]">
                  <div className="text-xs font-mono font-bold text-[#5C403B] uppercase">FRONTEND TESTS</div>
                  <div className="text-4xl font-black text-[#C8281E]">22</div>
                  <div className="text-xs text-[#5C403B]">Vitest atomic component checks, money formatting & state</div>
                </div>

                <div className="p-5 bg-white border border-[#231412]/15 shadow-sm text-center space-y-1 border-t-4 border-t-[#D4A359]">
                  <div className="text-xs font-mono font-bold text-[#5C403B] uppercase">BROWSER JOURNEYS</div>
                  <div className="text-4xl font-black text-[#D4A359]">8 / 8</div>
                  <div className="text-xs text-[#5C403B]">Playwright end-to-end commercial order-to-ledger journeys</div>
                </div>
              </div>

              {/* 3 Safeguard Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="p-3 bg-white border border-[#231412]/15 border-l-4 border-l-[#C8281E]">
                  <div className="text-[10px] font-mono font-bold text-[#C8281E]">ACCESS</div>
                  <div className="text-xs text-[#231412]">JWT authentication + role-based permissions (RBAC) + multi-tenant isolation</div>
                </div>
                <div className="p-3 bg-white border border-[#231412]/15 border-l-4 border-l-[#2D7D52]">
                  <div className="text-[10px] font-mono font-bold text-[#2D7D52]">SAFETY</div>
                  <div className="text-xs text-[#231412]">Inventory stockouts, negative cash guards & credit-limit exceptions</div>
                </div>
                <div className="p-3 bg-white border border-[#231412]/15 border-l-4 border-l-[#D4A359]">
                  <div className="text-[10px] font-mono font-bold text-[#D4A359]">CONSISTENCY</div>
                  <div className="text-xs text-[#231412]">ACID rollback boundaries + append-only SHA-256 audit trail on every write</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SLIDE 15: 14 / HANDOVER */}
          {currentSlide === 15 && (
            <motion.div
              key="s15"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"
            >
              <div className="lg:col-span-8 space-y-4">
                <div className="text-xs font-mono font-bold text-[#C8281E] uppercase">
                  ARTHLENS / OBJECT-ORIENTED METHODOLOGY
                </div>
                <h1 className="text-5xl font-black text-[#231412]">THANK YOU.</h1>
                <div className="text-xl font-bold text-[#5C403B]">Know the numbers. Move with intent.</div>

                <div className="border-t border-[#231412]/15 pt-3 space-y-2">
                  <div className="text-xs font-bold text-[#231412]">What this project demonstrates:</div>
                  <div className="space-y-1.5 text-xs text-[#5C403B]">
                    <div className="flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 bg-[#C8281E]" />
                      <span>Rich domain objects with enforceable invariants (Money value object, FIFO lots, atomic vouchers)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 bg-[#2D7D52]" />
                      <span>SOLID interfaces and reusable design patterns (23 patterns, Clean Architecture, repository ports)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 bg-[#D4A359]" />
                      <span>Financial correctness with human-governed AI (Zero-drift Khata, read-only DAGs, staged approvals)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 bg-[#231412]" />
                      <span>Complete formal UML diagrams documented in GitHub repository and README.md</span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 text-xs font-mono text-[#231412] font-semibold">
                  Abhay Pratap Singh (IIT2025109) • Ayush Mishra (IIT2025108) • Mayank Puri (IIT2025104)
                </div>
                <div className="text-xs font-mono text-[#C8281E]">
                  github.com/ayush-mg/arthlens
                </div>
              </div>

              {/* QR Code Card */}
              <div className="lg:col-span-4 flex flex-col items-center">
                <div className="bg-white border border-[#231412]/20 p-5 shadow-md flex flex-col items-center space-y-3">
                  <div className="relative w-40 h-40 border border-[#231412]/10 p-2 bg-white">
                    <Image
                      src="/presentation_qr.png"
                      alt="GitHub QR Code"
                      fill
                      className="object-contain p-1"
                    />
                  </div>
                  <div className="text-center font-mono">
                    <div className="text-[10px] text-[#5C403B] uppercase">SOURCE CODE</div>
                    <div className="text-sm font-bold text-[#231412]">GitHub</div>
                    <a
                      href="https://github.com/ayush-mg/arthlens"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-bold text-[#C8281E] flex items-center justify-center space-x-1 mt-0.5 hover:underline"
                    >
                      <span>SCAN / OPEN</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer Navigation Bar */}
      <footer className="h-10 border-t border-[#231412]/15 bg-[#FAF7F2] px-6 flex items-center justify-between text-xs font-mono text-[#9A7E78] shrink-0">
        <div className="flex items-center space-x-3">
          <span>OBJECT-ORIENTED METHODOLOGY • IIIT ALLAHABAD</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline text-[#5C403B]">ABHAY PRATAP SINGH, AYUSH MISHRA, MAYANK PURI</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={prevSlide}
            className="px-2.5 py-0.5 bg-white border border-[#231412]/20 text-[#231412] hover:bg-[#FAF7F2] hover:border-[#C8281E] flex items-center space-x-1 font-bold transition-colors"
          >
            <ArrowLeft className="w-3 h-3" />
            <span>PREV</span>
          </button>
          <button
            onClick={nextSlide}
            className="px-2.5 py-0.5 bg-[#C8281E] text-white border border-[#C8281E] hover:bg-[#A81E15] flex items-center space-x-1 font-bold transition-colors"
          >
            <span>NEXT</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </footer>
    </div>
  );
}
