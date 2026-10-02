import React from 'react';
import { DECISION_STATES } from '../decisionStates';

const SAFETY_INVARIANTS = [
  {
    name: "Fail-Closed Regulatory Invariant",
    rule: "Missing Gazette QCO records fail closed to NOT_VERIFIED_IN_CURRENT_CORPUS. The engine never declares a standard voluntarily conformant without positive gazette verification.",
    icon: "gavel",
  },
  {
    name: "Architectural Role Safety Invariant",
    rule: "Standards with UNKNOWN_ROLE, TEST_METHOD, CODE_OF_PRACTICE, or GUIDELINE are excluded from primary physical procurement recommendations and preserved only as supporting allied standards.",
    icon: "shield",
  },
  {
    name: "Requirement Consistency Pre-Screen",
    rule: "Contradictory specifications (e.g. Fe 500 + Fe 415, or Spun Iron Pipes + 33 kV Transformer) are blocked early, returning CONTRADICTORY_SPECIFICATIONS and primary=None without hallucinating.",
    icon: "block",
  },
  {
    name: "Deterministic Validator Veto Authority",
    rule: "All LLM extraction and explanation proposals are audited by a post-generation deterministic validator. The validator has absolute veto power over ungrounded standard designations.",
    icon: "verified_user",
  },
];

export default function AuditLogs({ health }) {
  const nodeCount = health?.indexed_standards || 6082;
  const qcoCount = health?.mandatory_qco_records || 327;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* Title */}
      <div className="w-full bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 shadow-xs">
            <span className="material-symbols-outlined text-[20px]">policy</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 font-display">
              Decision Policy &amp; Verification
            </h1>
            <p className="text-xs text-slate-500">
              Deterministic Safety Invariants, Calibration Transparency, and Decision State Registry
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-mono font-semibold">
            PROTOTYPE SCOPE: CED + ETD POLICY CONTROLS
          </span>
        </div>
      </div>

      {/* Offline Alert Banner if backend unreachable */}
      {health?.status === "OFFLINE" && (
        <div className="w-full bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-900 text-xs">
          <span className="material-symbols-outlined text-amber-600 text-lg">warning</span>
          <div className="flex-1">
            <span className="font-semibold block text-sm mb-0.5">Backend Gateway Offline</span>
            <span>{health.error}</span>
          </div>
        </div>
      )}

      {/* 4 Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Engine Release ID</span>
          <span className="text-sm font-bold font-mono text-slate-900 mt-1 block">
            {health?.release_id || (health?.status === "OFFLINE" ? "Unavailable (Offline)" : "Connecting...")}
          </span>
          <span className={`text-[11px] mt-1 block ${health?.release_id ? "text-emerald-700" : "text-slate-500"}`}>
            {health?.engine_version ? `Engine v${health.engine_version}` : "Release artifact"}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Corpus Scope</span>
          <span className="text-sm font-bold text-slate-900 mt-1 block">
            {nodeCount.toLocaleString()} indexed nodes
          </span>
          <span className="text-[11px] text-blue-700 mt-1 block">
            5,604 Indian-standard nodes in CED &amp; ETD
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Regulatory Corpus</span>
          <span className="text-sm font-bold text-slate-900 mt-1 block">
            {qcoCount} QCO Orders Indexed
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">
            BIS Mandatory Certification records
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Calibration Status</span>
          <span className="text-sm font-bold text-amber-700 mt-1 block">
            Empirical Thresholds
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Transparently uncalibrated to prevent false certainty
          </span>
        </div>
      </div>

      {/* Safety Invariants Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="font-display font-bold text-sm text-slate-900">
              Deterministic Safety Invariants &amp; Guardrails
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Architectural rules enforced deterministically without reliance on LLM self-policing
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-700 font-semibold">Deterministic Policy Enforcement</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {SAFETY_INVARIANTS.map((inv, i) => (
            <div key={i} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="material-symbols-outlined text-[18px]">{inv.icon}</span>
              </div>
              <div className="flex-1">
                <span className="text-xs font-bold text-slate-900 block font-display">{inv.name}</span>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">{inv.rule}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 10 Decision States Registry */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="font-display font-bold text-sm text-slate-900">
              Operational 10-State Decision Model
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Governs recommendation, expert review escalation, contradiction blocking, and calibrated abstention
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">SIH 2026 Aligned</span>
        </div>

        <div className="space-y-2">
          {Object.values(DECISION_STATES).map((ds, i) => (
            <div key={i} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${
                  ds.severity === "success" ? "bg-emerald-50 text-emerald-800 border-emerald-300" :
                  ds.severity === "danger" ? "bg-rose-50 text-rose-800 border-rose-300" :
                  ds.severity === "warning" ? "bg-amber-50 text-amber-800 border-amber-300" :
                  "bg-slate-100 text-slate-800 border-slate-300"
                }`}>
                  {ds.key}
                </span>
                <span className="text-xs font-semibold text-slate-700 hidden sm:inline">{ds.label}</span>
              </div>
              <span className="text-xs text-slate-600 sm:text-right max-w-xl">
                {ds.explanation}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
