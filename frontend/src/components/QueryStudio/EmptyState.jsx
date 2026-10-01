import React from 'react';

export default function EmptyState({ _onSelectExample }) {
  return (
    <div className="w-full bg-white rounded-2xl p-8 border border-slate-200/80 shadow-xs flex flex-col items-center text-center gap-6">
      <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shadow-2xs">
        <span className="material-symbols-outlined text-[36px]">manage_search</span>
      </div>

      <div className="max-w-md flex flex-col gap-2">
        <h3 className="text-lg font-bold font-display text-slate-900">
          Ready to Analyze Procurement Requirements
        </h3>
        <p className="text-xs text-slate-500 leading-relaxed">
          Enter a procurement description above or select one of the example specifications to retrieve authoritative Indian Standards with verified regulatory QCO status.
        </p>
      </div>

      {/* 3 Step Workflow */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl text-left pt-2">
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-emerald-600 text-white font-mono text-[11px] font-bold flex items-center justify-center">
              1
            </span>
            <span className="text-xs font-bold text-slate-800 font-sans">
              Enter Requirement
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Paste tender clauses or technical parameters (voltage, materials, dimensions).
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-emerald-600 text-white font-mono text-[11px] font-bold flex items-center justify-center">
              2
            </span>
            <span className="text-xs font-bold text-slate-800 font-sans">
              Analyze Standards
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Multi-stage search corroborates across 6,082 indexed CED &amp; ETD BIS standards.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-emerald-600 text-white font-mono text-[11px] font-bold flex items-center justify-center">
              3
            </span>
            <span className="text-xs font-bold text-slate-800 font-sans">
              Review &amp; Verify
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Obtain verified Indian Standards, scope evidence, and statutory QCO mandates.
          </p>
        </div>
      </div>
    </div>
  );
}
