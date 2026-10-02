import React from 'react';

export default function AbstentionCard({ decisionState, abstentionReason, _query, queryResult }) {
  if (!decisionState || decisionState === 'PRIMARY_RECOMMENDATION_AVAILABLE') return null;

  const contradictions = queryResult?.contradictions || [];
  const hasContradictions = contradictions.length > 0 || decisionState === 'CONTRADICTORY_SPECIFICATIONS';

  if (hasContradictions) {
    return (
      <div className="w-full bg-red-50/70 rounded-2xl p-6 border border-red-200 text-red-950 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[22px] text-red-600">error</span>
          <h4 className="font-bold text-sm text-red-950 font-display">
            Contradictory Technical Specifications Detected
          </h4>
        </div>
        <p className="text-xs text-red-800 leading-relaxed">
          {abstentionReason || "The procurement query specifies mutually conflicting technical parameters or incompatible product categories."}
        </p>

        {contradictions.length > 0 && (
          <div className="space-y-2">
            {contradictions.map((c, idx) => (
              <div key={idx} className="p-3 bg-white/90 rounded-xl border border-red-200 text-xs flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-red-800 text-[11px]">
                    {c.conflict_type || "SPECIFICATION_CONFLICT"}
                  </span>
                  {c.parameters && c.parameters.length > 0 && (
                    <span className="font-mono text-[10px] bg-red-50 px-2 py-0.5 rounded text-red-700 border border-red-200">
                      {c.parameters.join(' ⚡ ')}
                    </span>
                  )}
                </div>
                <p className="text-slate-700">{c.description}</p>
                {c.clarification_prompt && (
                  <p className="text-emerald-800 font-medium text-[11px] mt-0.5">
                    💡 Action: {c.clarification_prompt}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {queryResult?.clarification_prompt && contradictions.length === 0 && (
          <div className="p-3 bg-white/90 rounded-xl border border-red-200 text-xs text-slate-700">
            <strong className="block text-slate-900 font-semibold mb-1">Required Action:</strong>
            <p className="text-emerald-800">{queryResult.clarification_prompt}</p>
          </div>
        )}
      </div>
    );
  }

  if (decisionState === 'INSUFFICIENT_INFORMATION' || decisionState === 'CLARIFICATION_REQUIRED') {
    const clarifications = queryResult?.clarifications_needed || queryResult?.clarifications || [];
    const missingDisc = queryResult?.missing_discriminators || [];
    const prompt = queryResult?.clarification_prompt;

    return (
      <div className="w-full bg-orange-50/60 rounded-2xl p-6 border border-orange-200 text-orange-900 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-orange-700">tune</span>
          <h4 className="font-bold text-sm text-orange-950 font-display">
            Additional Specifications Needed for Precise Recommendation
          </h4>
        </div>
        <p className="text-xs text-orange-800 leading-relaxed">
          {abstentionReason || "The query specifies a general product category, but lacks critical distinguishing parameters required to select a single definitive standard."}
        </p>

        {prompt && (
          <div className="p-3 bg-white/90 rounded-xl border border-orange-200 text-xs text-slate-800">
            <strong className="block text-slate-900 font-semibold mb-0.5">Clarification Guidance:</strong>
            <p className="text-emerald-900 font-medium">{prompt}</p>
          </div>
        )}

        {clarifications.length > 0 && (
          <div className="p-3 bg-white/80 rounded-xl border border-orange-200/80 text-xs text-slate-700">
            <strong className="block text-slate-900 font-semibold mb-1">Required Clarifications:</strong>
            <ul className="list-disc list-inside space-y-1 text-slate-700">
              {clarifications.map((item, i) => (
                <li key={i}>{typeof item === 'string' ? item : item.question || JSON.stringify(item)}</li>
              ))}
            </ul>
          </div>
        )}

        {missingDisc.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap text-xs">
            <span className="font-mono text-slate-500 text-[11px] uppercase">Missing Discriminators:</span>
            {missingDisc.map((d, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-orange-100 text-orange-800 border border-orange-200 font-mono text-[11px]">
                {typeof d === 'string' ? d : d.attribute || JSON.stringify(d)}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (decisionState === 'NO_CONFIDENT_MATCH') {
    return (
      <div className="w-full bg-slate-50 rounded-2xl p-6 border border-slate-200 text-slate-800 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-slate-600">search_off</span>
          <h4 className="font-bold text-sm text-slate-900 font-display">
            No Confident Match in Prototype Corpus
          </h4>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {abstentionReason || "The retrieval and applicability engine searched the 6,082 indexed knowledge-graph nodes in Civil Engineering (CED) and Electrotechnical (ETD), but none achieved sufficient confidence."}
        </p>
        <p className="text-xs text-slate-500">
          Tip: Try rephrasing with specific technical terms, material grades, or equipment designations.
        </p>
      </div>
    );
  }

  if (decisionState === 'OUTSIDE_PROTOTYPE_COVERAGE') {
    return (
      <div className="w-full bg-purple-50/60 rounded-2xl p-6 border border-purple-200 text-purple-900 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-purple-700">domain_disabled</span>
          <h4 className="font-bold text-sm text-purple-950 font-display">
            Requirement Falls Outside Prototype Coverage
          </h4>
        </div>
        <p className="text-xs text-purple-800 leading-relaxed">
          This query is outside the current CED + ETD prototype coverage. The current prototype covers Civil Engineering (CED) and Electrotechnical (ETD) standards; other BIS departments are planned for future releases.
        </p>
      </div>
    );
  }

  if (decisionState === 'SUPERSEDED_STANDARD_IN_QUERY') {
    return (
      <div className="w-full bg-rose-50/60 rounded-2xl p-6 border border-rose-200 text-rose-900 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-rose-700">history_toggle_off</span>
          <h4 className="font-bold text-sm text-rose-950 font-display">
            Outdated / Superseded Standard Cited in Procurement Query
          </h4>
        </div>
        <p className="text-xs text-rose-800 leading-relaxed">
          {abstentionReason || "The tender text cites a superseded, withdrawn, or historical Indian Standard edition. Government procurement guidelines require citing the latest active standard."}
        </p>
      </div>
    );
  }

  return null;
}
