import React from 'react';

const STATE_CONFIG = {
  PRIMARY_RECOMMENDATION_AVAILABLE: {
    label: "Primary Recommendation Available",
    badgeClass: "bg-emerald-100 text-emerald-900 border-emerald-300",
    icon: "verified",
    iconColor: "text-emerald-600",
    description: "Authoritative Indian Standard identified and verified against technical requirements.",
  },
  CONDITIONAL_RECOMMENDATION: {
    label: "Conditional Recommendation",
    badgeClass: "bg-teal-100 text-teal-900 border-teal-300",
    icon: "fact_check",
    iconColor: "text-teal-600",
    description: "Standard applicable subject to specific installation, voltage, or ambient conditions.",
  },
  MULTIPLE_POSSIBLE_STANDARDS: {
    label: "Multiple Possible Standards",
    badgeClass: "bg-blue-100 text-blue-900 border-blue-300",
    icon: "difference",
    iconColor: "text-blue-600",
    description: "Multiple Indian Standards are applicable across different sub-clauses or construction types.",
  },
  EXPERT_REVIEW_REQUIRED: {
    label: "Expert Review Required",
    badgeClass: "bg-amber-100 text-amber-900 border-amber-300",
    icon: "engineering",
    iconColor: "text-amber-600",
    description: "Potentially relevant candidate found, but available scope evidence is insufficient for autonomous sign-off.",
  },
  INSUFFICIENT_INFORMATION: {
    label: "Insufficient Information",
    badgeClass: "bg-orange-100 text-orange-900 border-orange-300",
    icon: "help_outline",
    iconColor: "text-orange-600",
    description: "Essential technical parameters are absent in the query. Additional specification is needed.",
  },
  CLARIFICATION_REQUIRED: {
    label: "Clarification Required",
    badgeClass: "bg-orange-100 text-orange-900 border-orange-300",
    icon: "help_outline",
    iconColor: "text-orange-600",
    description: "Essential technical parameters are absent in the query. Additional specification is needed.",
  },
  AMBIGUOUS_QUERY_VOLTAGE_OR_MATERIAL_ABSENT: {
    label: "Ambiguous Query Parameters",
    badgeClass: "bg-yellow-100 text-yellow-900 border-yellow-300",
    icon: "warning",
    iconColor: "text-yellow-600",
    description: "Key distinguishing parameters (such as operating voltage or material grade) are not specified.",
  },
  NO_CONFIDENT_MATCH: {
    label: "No Confident Match",
    badgeClass: "bg-slate-100 text-slate-800 border-slate-300",
    icon: "search_off",
    iconColor: "text-slate-500",
    description: "No standard in the indexed prototype corpus met technical applicability thresholds.",
  },
  OUTSIDE_PROTOTYPE_COVERAGE: {
    label: "Outside Prototype Coverage",
    badgeClass: "bg-purple-100 text-purple-900 border-purple-300",
    icon: "domain_disabled",
    iconColor: "text-purple-600",
    description: "Requirement falls outside Civil Engineering (CED) and Electrotechnical (ETD) prototype scope.",
  },
  SUPERSEDED_STANDARD_IN_QUERY: {
    label: "Superseded Standard Cited",
    badgeClass: "bg-rose-100 text-rose-900 border-rose-400",
    icon: "history_toggle_off",
    iconColor: "text-rose-600",
    description: "The specification cites a withdrawn or historical standard edition that must be updated.",
  },
  CONTRADICTORY_SPECIFICATIONS: {
    label: "Contradictory Specifications",
    badgeClass: "bg-red-100 text-red-900 border-red-300",
    icon: "error",
    iconColor: "text-red-600",
    description: "Mutually conflicting technical parameters or cross-domain product combinations were detected.",
  },
};

export default function DecisionSummary({ decisionState, abstentionReason, claimLevel, language }) {
  const config = STATE_CONFIG[decisionState] || {
    label: decisionState || "Decision Pending",
    badgeClass: "bg-slate-100 text-slate-800 border-slate-200",
    icon: "info",
    iconColor: "text-slate-600",
    description: "System evaluation completed.",
  };

  const getLanguageLabel = (code) => {
    switch (code) {
      case 'hi': return 'Hindi (हिन्दी)';
      case 'gu': return 'Gujarati (ગુજરાતી)';
      case 'hinglish': return 'Hinglish (Code-Mixed)';
      default: return 'English';
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-start sm:items-center gap-3.5">
        <div className={`w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center shrink-0 ${config.iconColor}`}>
          <span className="material-symbols-outlined text-[24px]">{config.icon}</span>
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`px-2.5 py-0.5 rounded-md text-xs font-mono font-bold uppercase tracking-wide border ${config.badgeClass}`}>
              {config.label}
            </span>
            {claimLevel && (
              <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Claim: {claimLevel}
              </span>
            )}
            {language && (
              <span className="text-[11px] font-mono text-slate-600 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-slate-400">translate</span>
                <span>Language: {getLanguageLabel(language)}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 mt-1">
            {abstentionReason || config.description}
          </p>
        </div>
      </div>
    </div>
  );
}
