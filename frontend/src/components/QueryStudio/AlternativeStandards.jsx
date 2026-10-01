import React from 'react';

export default function AlternativeStandards({
  candidates = [],
  alliedStandards = [],
  rejectedCandidates = [],
  _onSelectStandard,
}) {
  const hasCandidates = candidates && candidates.length > 0;
  const hasAllied = alliedStandards && alliedStandards.length > 0;
  const hasRejected = rejectedCandidates && rejectedCandidates.length > 0;

  if (!hasCandidates && !hasAllied && !hasRejected) return null;

  // Group Allied Standards by Architectural Role (Mentor review Part 23)
  const getRoleCategory = (allied) => {
    const role = (allied.standard_role || allied.role || "").toUpperCase();
    const rel = (allied.relationship || "").toLowerCase();
    const title = (allied.title || "").toLowerCase();
    const desig = (allied.standard_designation || allied.designation || "").toLowerCase();

    if (role === "TEST_METHOD" || rel.includes("test") || title.includes("method of test") || title.includes("methods of test") || desig.includes("10810") || desig.includes("516")) {
      return "Test Methods & Sampling Procedures";
    }
    if (role === "COMPONENT" || rel.includes("material") || title.includes("conductor") || title.includes("aggregate") || title.includes("profiles")) {
      return "Components & Feedstock Materials";
    }
    if (role === "DESIGN_CODE" || role === "CODE_OF_PRACTICE" || rel.includes("code") || title.includes("code of practice")) {
      return "Design Codes & Codes of Practice";
    }
    if (role === "INSTALLATION_CODE" || rel.includes("installation") || title.includes("installation") || title.includes("laying")) {
      return "Installation & Maintenance Codes";
    }
    if (role === "DIMENSIONAL_MOUNTING" || rel.includes("dimensional") || title.includes("dimensions")) {
      return "Dimensional & Mounting Envelopes";
    }
    return "Normative References & Auxiliary Standards";
  };

  const groupedAllied = {};
  if (hasAllied) {
    for (const allied of alliedStandards) {
      const cat = getRoleCategory(allied);
      if (!groupedAllied[cat]) groupedAllied[cat] = [];
      groupedAllied[cat].push(allied);
    }
  }

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col gap-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-blue-600">hub</span>
          <h3 className="font-bold text-sm text-slate-900 font-display">
            Related &amp; Alternative Standards
          </h3>
        </div>
        <span className="text-xs text-slate-500">
          Candidate standards, normative references, and test methods
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Alternative Candidates */}
        {hasCandidates && (
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-blue-600">view_list</span>
              Other Candidate Standards ({candidates.length})
            </span>
            <div className="space-y-2">
              {candidates.map((cand, idx) => {
                const desig = cand.standard_designation || cand.designation || `Candidate #${idx + 1}`;
                const rawScore = typeof cand.confidence_score === 'number'
                  ? cand.confidence_score
                  : (typeof cand.rerank_score === 'number' ? cand.rerank_score : null);

                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors flex flex-col gap-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-900">{desig}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                        {rawScore !== null ? `Match Score: ${rawScore.toFixed(2)} (Uncalibrated)` : 'Match Score: —'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2">{cand.title}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Allied Standards: Grouped by Architectural Role (Part 23) */}
        {hasAllied && (
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-emerald-600">link</span>
              Allied Standards by Role ({alliedStandards.length})
            </span>
            <div className="space-y-4">
              {Object.entries(groupedAllied).map(([category, items]) => (
                <div key={category} className="flex flex-col gap-1.5">
                  <span className="text-[11px] font-bold text-slate-500 uppercase font-mono">
                    {category} ({items.length})
                  </span>
                  <div className="space-y-1.5">
                    {items.map((allied, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col gap-0.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {allied.standard_designation || allied.designation}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase">
                            {allied.relationship || "Normative Reference"}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 line-clamp-1">
                          {allied.title || allied.reason || "Referenced Indian Standard specification."}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Rejected Candidates with Reason */}
      {hasRejected && (
        <div className="flex flex-col gap-3 pt-3 border-t border-slate-100">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[15px] text-rose-600">cancel</span>
            Rejected Candidates ({rejectedCandidates.length})
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {rejectedCandidates.map((rej, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl border border-rose-100 bg-rose-50/30 flex flex-col gap-1 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-rose-950">
                    {rej.designation || rej.standard_designation}
                  </span>
                  <span className="text-[10px] font-mono text-rose-700">REJECTED</span>
                </div>
                <p className="text-[11px] text-rose-800 line-clamp-2">
                  {rej.rejection_reason || rej.reason || "Did not satisfy attribute or scope constraints."}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
