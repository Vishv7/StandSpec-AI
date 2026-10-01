import React from 'react';

export default function EvidenceSummary({ standard }) {
  if (!standard) return null;

  const bundle = standard.evidence_bundle || {};
  const readiness = bundle.readiness?.evidence_dimensions || {};

  const DIMENSIONS = [
    { key: "identity_ready", label: "Identity", icon: "badge", desc: "Designation, Title, Part & Department verified" },
    { key: "scope_ready", label: "Scope", icon: "menu_book", desc: "Standard scope clause extracted from authoritative text" },
    { key: "applicability_ready", label: "Applicability", icon: "tune", desc: "Product, voltage, and material compatibility verified" },
    { key: "lifecycle_ready", label: "Lifecycle", icon: "schedule", desc: "Active edition, year, and amendment status checked" },
    { key: "regulatory_ready", label: "Regulatory", icon: "gavel", desc: "Quality Control Order (QCO) and statutory mandate checked" },
    { key: "provenance_ready", label: "Provenance", icon: "source", desc: "BIS source portal and document trace recorded" },
  ];

  return (
    <div className="w-full bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">fact_check</span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
            Evidence Corroboration Dimensions
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          Six-point evidentiary validation
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {DIMENSIONS.map((dim) => {
          const isReady = readiness[dim.key] !== false;
          return (
            <div
              key={dim.key}
              className={`p-2.5 rounded-xl border flex flex-col gap-1 transition-all ${
                isReady
                  ? 'bg-emerald-50/40 border-emerald-200/80 text-emerald-900'
                  : 'bg-amber-50/40 border-amber-200/80 text-amber-900'
              }`}
              title={dim.desc}
            >
              <div className="flex items-center justify-between">
                <span className="material-symbols-outlined text-[16px] text-slate-600">
                  {dim.icon}
                </span>
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                  isReady ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                }`}>
                  {isReady ? 'VERIFIED' : 'PARTIAL'}
                </span>
              </div>
              <span className="text-xs font-bold tracking-tight text-slate-800 mt-1">
                {dim.label}
              </span>
              <span className="text-[10px] text-slate-500 leading-tight">
                {dim.desc}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
