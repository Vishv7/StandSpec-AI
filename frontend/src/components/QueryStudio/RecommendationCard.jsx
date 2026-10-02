import React, { useState } from 'react';

export default function RecommendationCard({
  standard,
  isReviewCandidate = false,
  decisionState,
  abstentionReason,
}) {
  const [copied, setCopied] = useState(false);

  if (!standard) return null;

  const designation = standard.standard_designation || standard.designation || "Unknown Designation";
  const title = standard.title || "No Title Available";
  const department = standard.evidence_bundle?.department || standard.department || "NOT_VERIFIED";
  const applicability = standard.applicability || {};
  const matchedAttrs = applicability.matched_attributes || [];
  const regulatory = standard.regulatory || {};
  const lifecycle = standard.lifecycle || {};
  const isMandatory = regulatory.state === "MANDATORY_CONFIRMED" || regulatory.state === "MANDATORY_CONDITIONALLY_APPLICABLE" || regulatory.is_mandatory === true;
  const amendments = standard.amendments || lifecycle.applicable_amendments || [];

  const handleCopy = () => {
    navigator.clipboard.writeText(designation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Determine readiness badge based on verified decision state and claim level
  let readinessBadge = {
    label: standard.claim_level === "PRIMARY_RECOMMENDATION" ? "Primary Recommendation" : "Identified Candidate",
    class: "bg-emerald-50 text-emerald-800 border-emerald-300",
    icon: "verified",
  };

  if (isReviewCandidate || decisionState === 'EXPERT_REVIEW_REQUIRED') {
    readinessBadge = {
      label: "Expert Review Required",
      class: "bg-amber-50 text-amber-800 border-amber-300",
      icon: "engineering",
    };
  } else if (decisionState === 'CONDITIONAL_RECOMMENDATION') {
    readinessBadge = {
      label: "Conditional Recommendation",
      class: "bg-teal-50 text-teal-800 border-teal-300",
      icon: "fact_check",
    };
  } else if (decisionState === 'INSUFFICIENT_INFORMATION') {
    readinessBadge = {
      label: "Insufficient Evidence",
      class: "bg-slate-100 text-slate-800 border-slate-300",
      icon: "help_outline",
    };
  }

  return (
    <div className={`w-full bg-white rounded-2xl p-6 border shadow-xs flex flex-col gap-5 ${
      isReviewCandidate ? 'border-amber-200 bg-amber-50/10' : 'border-slate-200'
    }`}>
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              Department: {department}
            </span>
            <span className={`flex items-center gap-1 font-mono text-xs font-bold px-2.5 py-0.5 rounded border ${readinessBadge.class}`}>
              <span className="material-symbols-outlined text-[14px]">{readinessBadge.icon}</span>
              <span>{readinessBadge.label}</span>
            </span>
            {isReviewCandidate && (
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                Candidate for Engineering Review
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1">
            <h3 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900">
              {designation}
            </h3>
            <button
              type="button"
              onClick={handleCopy}
              className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
              title="Copy standard designation"
            >
              <span className="material-symbols-outlined text-[18px]">
                {copied ? 'check' : 'content_copy'}
              </span>
            </button>
          </div>

          <p className="text-sm font-medium text-slate-700 mt-0.5 leading-snug">
            {title}
          </p>
        </div>

        {/* Regulatory Badge */}
        {isMandatory && (
          <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 self-start shrink-0 max-w-xs">
            <span className="material-symbols-outlined text-[18px] text-amber-700 shrink-0">gavel</span>
            <div className="text-[11px] leading-tight">
              <span className="font-bold block text-amber-950">Indexed Regulatory Evidence</span>
              <span className="text-amber-800 line-clamp-2">
                {regulatory.qco_order || regulatory.order_title || "Mandatory certification under published QCO"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Prominent Superseded Alert */}
      {(lifecycle.is_superseded || lifecycle.lifecycle_state === "VERIFIED_SUPERSEDED") && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 flex items-start gap-3 text-xs">
          <span className="material-symbols-outlined text-rose-600 text-xl shrink-0 mt-0.5">warning</span>
          <div className="flex-1">
            <strong className="font-bold text-sm block text-rose-950">SUPERSEDED STANDARD EDITION</strong>
            <p className="mt-1 text-rose-800 leading-relaxed">
              Candidate edition <strong>{designation}</strong> appears superseded according to indexed lifecycle records. Modern revision: <strong>{lifecycle.recommended_edition || lifecycle.superseded_by || "Check current catalog"}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* Conflicting Regulatory Records Alert */}
      {regulatory.state === "CONFLICTING_EVIDENCE" && (
        <div className="p-3.5 rounded-xl bg-yellow-50 border border-yellow-300 text-yellow-900 flex items-start gap-2.5 text-xs">
          <span className="material-symbols-outlined text-yellow-700 text-lg shrink-0 mt-0.5">balance</span>
          <div>
            <strong className="font-semibold block text-yellow-950">Conflicting Regulatory Records</strong>
            <p className="mt-0.5 text-yellow-800">
              Contradictory regulatory mandates were identified across indexed sources. Authoritative confirmation from the relevant Ministry notification is recommended.
            </p>
          </div>
        </div>
      )}

      {/* Evidence-grounded Match Summary */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono">
          Corroborated Match Evidence
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px] text-emerald-600 shrink-0 mt-0.5">check_circle</span>
            <span className="text-slate-700">
              <strong>Applicability:</strong> {applicability.applicability_state || (matchedAttrs.length > 0 ? "APPLICABLE" : "EVALUATED")}
            </span>
          </div>

          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px] text-emerald-600 shrink-0 mt-0.5">check_circle</span>
            <span className="text-slate-700">
              <strong>Attributes:</strong> {matchedAttrs.length > 0 ? matchedAttrs.join(', ') : 'Product family verified'}
            </span>
          </div>

          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px] text-emerald-600 shrink-0 mt-0.5">check_circle</span>
            <span className="text-slate-700">
              <strong>Lifecycle:</strong> {lifecycle.lifecycle_state || "LIFECYCLE_UNKNOWN"}
              {amendments.length > 0 ? ` (${amendments.length} amendments)` : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Caveat or Review Warning if needed */}
      {(abstentionReason || isReviewCandidate) && (
        <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 text-amber-900 flex items-start gap-2.5 text-xs">
          <span className="material-symbols-outlined text-[18px] text-amber-700 shrink-0 mt-0.5">info</span>
          <div>
            <strong className="font-semibold block">Important Engineering Note:</strong>
            <p className="mt-0.5 text-amber-800 leading-relaxed">
              {abstentionReason || "This standard was identified as the closest candidate, but verified scope text in the knowledge base is insufficient to fully confirm compliance. Human engineering review is advised."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
