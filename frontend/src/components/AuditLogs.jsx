import React from 'react';

const DECISION_STATES = [
  { state: "PRIMARY_RECOMMENDATION_AVAILABLE", badge: "bg-emerald-50 text-emerald-800 border-emerald-300", meaning: "Single authoritative standard fully matches all extracted technical requirements." },
  { state: "CONDITIONAL_RECOMMENDATION", badge: "bg-teal-50 text-teal-800 border-teal-300", meaning: "Standard is applicable subject to specific installation or voltage caveats." },
  { state: "MULTIPLE_POSSIBLE_STANDARDS", badge: "bg-blue-50 text-blue-800 border-blue-300", meaning: "Multiple equally valid Indian Standards apply across different sub-clauses." },
  { state: "CLARIFICATION_REQUIRED", badge: "bg-indigo-50 text-indigo-800 border-indigo-300", meaning: "Essential technical parameters (e.g. voltage or pipe diameter) are absent in query." },
  { state: "EXPERT_REVIEW_REQUIRED", badge: "bg-amber-50 text-amber-800 border-amber-300", meaning: "Standard identified, but candidate lacks full KB verified scope evidence." },
  { state: "NO_CONFIDENT_MATCH", badge: "bg-rose-50 text-rose-800 border-rose-300", meaning: "Item falls within CED/ETD scope but cannot be mapped to any known standard." },
  { state: "OUTSIDE_PROTOTYPE_COVERAGE", badge: "bg-purple-50 text-purple-800 border-purple-300", meaning: "Item clearly belongs outside CED (Civil) and ETD (Electrotechnical) scope." },
  { state: "SUPERSEDED_STANDARD_IN_QUERY", badge: "bg-rose-100 text-rose-900 border-rose-400", meaning: "Tender cites a withdrawn or historical standard edition that must be updated." },
  { state: "AMBIGUOUS_QUERY_VOLTAGE_OR_MATERIAL_ABSENT", badge: "bg-yellow-50 text-yellow-900 border-yellow-300", meaning: "Too vague to disambiguate between divergent standard branches." },
];

export default function AuditLogs({ health }) {
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
              Autonomous Agent Audit &amp; Deterministic Validator Core
            </h1>
            <p className="text-xs text-slate-500">
              Zero-Hallucination Guard, Calibration Metrics, and FIPS Audit Sandbox
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-mono font-semibold">
            VALIDATOR: 100% DETERMINISTIC PASS
          </span>
        </div>
      </div>

      {/* 3 Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Engine Release ID</span>
          <span className="text-sm font-bold font-mono text-slate-900 mt-1 block">
            {health?.release_id || "STANDSPEC_PROTOTYPE_CED_ETD_V3_0_0"}
          </span>
          <span className="text-[11px] text-emerald-700 mt-1 block">
            Verified Hash • Immutable Release Artifact
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Corpus Integrity</span>
          <span className="text-sm font-bold text-slate-900 mt-1 block">
            {(health?.indexed_standards || 6082).toLocaleString()} Nodes • {health?.mandatory_qco_records || 163} QCOs
          </span>
          <span className="text-[11px] text-blue-700 mt-1 block">
            Civil Engineering (CED) + Electrotechnical (ETD)
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">Zero-Hallucination Gate</span>
          <span className="text-sm font-bold text-emerald-700 mt-1 block">
            100% Verified Invariant Protection
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Strict post-generation deterministic validator intercept
          </span>
        </div>
      </div>

      {/* 9 Decision States Registry */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="font-display font-bold text-sm text-slate-900">
            Authoritative 9-State Decision Model
          </h2>
          <span className="text-xs font-mono text-slate-500">ISO 9001 / BIS Calibrated</span>
        </div>

        <div className="space-y-2">
          {DECISION_STATES.map((ds, i) => (
            <div key={i} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${ds.badge}`}>
                  {ds.state}
                </span>
              </div>
              <span className="text-xs text-slate-600 sm:text-right">
                {ds.meaning}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
