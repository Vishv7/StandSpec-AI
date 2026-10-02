import React, { useState } from 'react';

export default function ProgressiveEvidenceTabs({ standard, queryResult }) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!standard && !queryResult) return null;

  const bundle = standard?.evidence_bundle || {};
  const scope = bundle.scope || {};
  const applicability = standard?.applicability || queryResult?.applicability || {};
  const regulatory = standard?.regulatory || queryResult?.regulatory || {};
  const lifecycle = standard?.lifecycle || queryResult?.lifecycle || {};
  const evalTrace = applicability?.evaluation_trace || [];
  const amendments = standard?.amendments || lifecycle?.applicable_amendments || [];
  const decisionTrace = queryResult?.decision_trace || standard?.decision_trace || [];
  const failureTrace = queryResult?.failure_trace || standard?.failure_trace || [];

  const TABS = [
    { id: 'overview', label: 'Overview', icon: 'visibility' },
    { id: 'scope', label: 'Scope Evidence', icon: 'menu_book' },
    { id: 'applicability', label: 'Technical Applicability', icon: 'tune' },
    { id: 'lifecycle', label: 'Lifecycle & Validity', icon: 'schedule' },
    { id: 'regulatory', label: 'Regulatory Evidence', icon: 'gavel' },
    { id: 'trace', label: 'Decision Trace', icon: 'policy' },
  ];

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
      {/* Tab Navigation Header */}
      <div className="flex items-center gap-1 p-2 bg-slate-50 border-b border-slate-200 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-white text-emerald-800 shadow-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <span className="material-symbols-outlined text-[17px] text-slate-500">
              {tab.icon}
            </span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Body */}
      <div className="p-6">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="flex flex-col gap-5">
            <div>
              <h4 className="text-sm font-bold text-slate-900 font-display">
                Recommendation Overview &amp; Key Parameters
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Summary of technical alignment and evidentiary checks
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Standard Designation</span>
                <span className="text-sm font-bold font-mono text-slate-900">
                  {standard?.standard_designation || standard?.designation || "—"}
                </span>
                <span className="text-xs text-slate-600 line-clamp-2">
                  {standard?.title || "—"}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Regulatory State</span>
                <span className={`text-sm font-bold font-mono ${
                  regulatory.state === "MANDATORY_CONFIRMED" ? 'text-amber-800' : 'text-slate-700'
                }`}>
                  {regulatory.state || "NOT_VERIFIED_IN_CURRENT_CORPUS"}
                </span>
                <span className="text-xs text-slate-600">
                  {regulatory.order_title || regulatory.qco_order || "No matching regulatory record in indexed corpus"}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Lifecycle State</span>
                <span className="text-sm font-bold font-mono text-emerald-800">
                  {lifecycle.lifecycle_state || "LIFECYCLE_UNKNOWN"}
                </span>
                <span className="text-xs text-slate-600">
                  Edition: {lifecycle.recommended_edition || standard?.standard_designation || "Unverified"}
                </span>
              </div>
            </div>

            {/* Matched Attributes Pill Row */}
            <div className="flex flex-col gap-2 pt-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Matched Technical Discriminators
              </span>
              <div className="flex flex-wrap gap-2">
                {(applicability.matched_attributes || []).length > 0 ? (
                  applicability.matched_attributes.map((attr, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-mono font-medium flex items-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-[14px]">check</span>
                      <span>{attr}</span>
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-500 italic">No specific discriminators matched</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCOPE EVIDENCE */}
        {activeTab === 'scope' && (
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900 font-display">
                Scope Clause Evidence
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Verbatim standard scope text extracted from indexed standards knowledge graph
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-serif leading-relaxed text-slate-800 italic">
              "{scope.raw_scope || scope.scope_text || standard?.scope_evidence || standard?.scope || "Scope text not available in indexed corpus."}"
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white">
                <span className="text-xs font-bold text-slate-700 block mb-1">Inclusions / Covered Applications:</span>
                <p className="text-xs text-slate-600">
                  {scope.inclusions && scope.inclusions.length > 0
                    ? scope.inclusions.join(', ')
                    : "Not specified in current evidence."}
                </p>
              </div>

              <div className="p-3.5 rounded-xl border border-slate-200 bg-white">
                <span className="text-xs font-bold text-slate-700 block mb-1">Exclusions / Non-applicable uses:</span>
                <p className="text-xs text-slate-600">
                  {scope.exclusions && scope.exclusions.length > 0
                    ? scope.exclusions.join(', ')
                    : "Not specified in current evidence."}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: TECHNICAL APPLICABILITY — Rendered dynamically from applicability.evaluation_trace */}
        {activeTab === 'applicability' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900 font-display">
                  Technical Applicability Evaluation Trace
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Granular parameter comparison between procurement requirements and standard scope
                </p>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                applicability.applicability_state === "APPLICABLE" ? "bg-emerald-100 text-emerald-800" :
                applicability.applicability_state === "CONDITIONALLY_APPLICABLE" ? "bg-teal-100 text-teal-800" :
                "bg-amber-100 text-amber-800"
              }`}>
                State: {applicability.applicability_state || "UNKNOWN"}
              </span>
            </div>

            {evalTrace.length > 0 ? (
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-mono uppercase text-[11px]">
                    <tr>
                      <th className="p-3">Attribute</th>
                      <th className="p-3">Query Requirement</th>
                      <th className="p-3">Standard Evidence</th>
                      <th className="p-3">Source</th>
                      <th className="p-3">Match State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {evalTrace.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="p-3 font-semibold text-slate-900 font-mono">{row.attribute || "—"}</td>
                        <td className="p-3 text-slate-700">{row.query_value || "—"}</td>
                        <td className="p-3 text-slate-600 max-w-xs truncate" title={row.standard_evidence}>{row.standard_evidence || "—"}</td>
                        <td className="p-3 font-mono text-[11px] text-slate-500">{row.source || "—"}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                            row.state === "MATCH" ? "bg-emerald-100 text-emerald-800" :
                            row.state === "MISMATCH" ? "bg-rose-100 text-rose-800" :
                            "bg-slate-100 text-slate-700"
                          }`}>
                            {row.state || "EVALUATED"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600">
                <p>Applicability state: <strong>{applicability.applicability_state || "EVALUATED"}</strong></p>
                <p className="mt-1 text-slate-500">
                  Matched attributes: {(applicability.matched_attributes || []).join(", ") || "Product classification"}
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: LIFECYCLE & AMENDMENTS */}
        {activeTab === 'lifecycle' && (
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900 font-display">
                Lifecycle, Editions &amp; Amendments
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Publication status, edition resolution, supersession relationships, and amendment chain
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Candidate Edition</span>
                <span className="text-sm font-bold font-mono text-slate-900">
                  {lifecycle.candidate_edition || standard?.standard_designation || standard?.designation || "—"}
                </span>
                <span className="text-xs text-slate-600">
                  Evaluated as of: {lifecycle.evaluation_as_of_date || queryResult?.evaluation_as_of_date || "Current"}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Recommended Active Edition</span>
                <span className="text-sm font-bold font-mono text-slate-900">
                  {lifecycle.recommended_edition || standard?.standard_designation || "—"}
                </span>
                <span className="text-xs font-mono font-semibold text-emerald-700">
                  Lifecycle State: {lifecycle.lifecycle_state || "LIFECYCLE_UNKNOWN"}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Supersession Status</span>
                <span className="text-sm font-bold text-slate-800">
                  {lifecycle.is_superseded ? "SUPERSEDED" : (lifecycle.is_superseded === false ? "ACTIVE (NOT SUPERSEDED)" : "STATUS UNVERIFIED")}
                </span>
                {lifecycle.superseded_by && (
                  <span className="text-xs text-rose-700 font-mono">
                    Superseded by: {lifecycle.superseded_by}
                  </span>
                )}
              </div>
            </div>

            {/* Amendments Section (PS 26108 P0) */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
                Applicable Amendments
              </span>
              {amendments.length > 0 ? (
                <div className="space-y-1.5">
                  {amendments.map((am, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center justify-between">
                      <span className="font-mono font-semibold text-slate-800">
                        {typeof am === "string" ? am : am.amendment_number || `Amendment ${i + 1}`}
                      </span>
                      {am.effective_date && (
                        <span className="text-slate-500 font-mono text-[11px]">Effective: {am.effective_date}</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-slate-100 text-xs font-mono text-slate-600">
                  AMENDMENT_DATA_UNAVAILABLE
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: REGULATORY */}
        {activeTab === 'regulatory' && (
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900 font-display">
                Regulatory Evidence &amp; Mandatory Certification
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Published Quality Control Orders (QCO) and statutory certification schemes
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase font-bold text-slate-600">Regulatory State</span>
                <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                  regulatory.state === "MANDATORY_CONFIRMED"
                    ? 'bg-amber-100 text-amber-900 border border-amber-300'
                    : (regulatory.state === "CONFLICTING_EVIDENCE"
                        ? 'bg-rose-100 text-rose-900 border border-rose-300'
                        : 'bg-slate-200 text-slate-700')
                }`}>
                  {regulatory.state || "NOT_VERIFIED_IN_CURRENT_CORPUS"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block">Order Title:</span>
                  <span className="font-semibold text-slate-900">{regulatory.order_title || regulatory.qco_order || "Not indexed in current corpus"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Order Number / Reference:</span>
                  <span className="font-mono text-slate-800">{regulatory.order_number || regulatory.qco_order_number || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Gazette Reference:</span>
                  <span className="font-mono text-slate-800">{regulatory.gazette_reference || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Effective Date:</span>
                  <span className="font-mono text-slate-800">{regulatory.effective_date || "—"}</span>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-slate-200 text-xs text-slate-700">
                <p>
                  {regulatory.state === "MANDATORY_CONFIRMED"
                    ? `Indexed regulatory evidence indicates mandatory certification under ${regulatory.order_title || "published order"}.`
                    : "No matching regulatory record was found in the indexed regulatory corpus. This does not establish voluntary status or exemption."}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: DECISION TRACE — Real backend decision_trace[] */}
        {activeTab === 'trace' && (
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900 font-display">
                Decision Trace &amp; Audit Trail
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Sequential execution trace of deterministic validator gates and decision rationale
              </p>
            </div>

            <div className="space-y-2 text-xs">
              {decisionTrace.length > 0 ? (
                decisionTrace.map((step, i) => (
                  <div key={i} className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                    <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 mt-0.5">
                      #{i + 1}
                    </span>
                    <span className="text-slate-800 font-mono leading-relaxed">
                      {typeof step === "string" ? step : JSON.stringify(step)}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 font-mono text-xs">
                  Deterministic pipeline executed. No intermediate gate warnings logged.
                </div>
              )}

              {failureTrace.length > 0 && (
                <div className="mt-3 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex flex-col gap-1.5">
                  <span className="font-bold text-rose-950">Safety Intercept Warnings:</span>
                  {failureTrace.map((f, i) => (
                    <div key={i} className="font-mono text-[11px] text-rose-800">
                      • {typeof f === "string" ? f : JSON.stringify(f)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
