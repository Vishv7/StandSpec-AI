import React from 'react';

const ANALYSIS_STAGES = [
  { step: 1, label: "Understanding Requirements", desc: "Extracting product, voltage, material, and rating attributes" },
  { step: 2, label: "Searching BIS Standards", desc: "Combined search ranking across CED & ETD indexed corpus" },
  { step: 3, label: "Verifying Applicability", desc: "Validating candidate scope, inclusions, and attribute constraints" },
  { step: 4, label: "Checking Evidence", desc: "Corroborating lifecycle validity and statutory QCO mandates" },
  { step: 5, label: "Finalizing Decision", desc: "Executing evidence-grounded decision policy and safety gate" },
];

export default function AnalysisProgress({ mode }) {
  const isAgentMode = mode === 'auto' || mode === 'llm';

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <span className="material-symbols-outlined text-[20px] animate-spin">sync</span>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 font-display">
              Analyzing Procurement Requirement
            </h3>
            <p className="text-xs text-slate-500">
              Executing multi-stage regulatory corroboration pipeline
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700">
            {isAgentMode ? "LLM-assisted requirement understanding" : "Local deterministic analysis"}
          </span>
        </div>
      </div>

      {/* Stage Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {ANALYSIS_STAGES.map((stg) => (
          <div
            key={stg.step}
            className="p-3.5 rounded-xl border border-emerald-100 bg-emerald-50/30 flex flex-col gap-1.5 transition-all"
          >
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-emerald-600 text-white font-mono text-[10px] font-bold flex items-center justify-center">
                {stg.step}
              </span>
              <span className="text-xs font-bold text-slate-800 tracking-tight">
                {stg.label}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight">
              {stg.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
