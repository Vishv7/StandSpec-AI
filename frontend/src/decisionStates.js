/**
 * StandSpec AI — Central Decision State Registry
 * Implements PS 26108 Section 38: Canonical decision state definitions,
 * visual severities, primary eligibility, review expectations, and recommended actions.
 */

export const DECISION_STATES = {
  PRIMARY_RECOMMENDATION_AVAILABLE: {
    key: "PRIMARY_RECOMMENDATION_AVAILABLE",
    label: "Primary Recommendation Available",
    explanation: "Primary Indian Standard identified with verified scope and lifecycle evidence within CED/ETD coverage.",
    severity: "success", // success, warning, danger, neutral
    primaryAllowed: true,
    reviewExpected: false,
    nextAction: "Review full evidence bundle, amendments, and applicable regulatory order details before procurement inclusion.",
    badgeClass: "badge-success",
  },
  CONDITIONAL_RECOMMENDATION: {
    key: "CONDITIONAL_RECOMMENDATION",
    label: "Conditional Recommendation",
    explanation: "Standard is technically applicable subject to specific procurement conditions, parameter ratings, or material grades.",
    severity: "warning",
    primaryAllowed: true,
    reviewExpected: false,
    nextAction: "Verify specific design parameters, ratings, and application constraints against procurement specification.",
    badgeClass: "badge-warning",
  },
  MULTIPLE_POSSIBLE_STANDARDS: {
    key: "MULTIPLE_POSSIBLE_STANDARDS",
    label: "Multiple Plausible Standards",
    explanation: "Multiple candidate standards match the procurement description; specification lacks discriminating attributes.",
    severity: "warning",
    primaryAllowed: false,
    reviewExpected: true,
    nextAction: "Clarify technical discriminators (e.g., application medium, voltage class, mounting type) to narrow candidates.",
    badgeClass: "badge-warning",
  },
  INSUFFICIENT_INFORMATION: {
    key: "INSUFFICIENT_INFORMATION",
    label: "Insufficient Information",
    explanation: "Input specification lacks core technical attributes (e.g. material, application, ratings) required for definitive match.",
    severity: "warning",
    primaryAllowed: false,
    reviewExpected: true,
    nextAction: "Provide detailed technical specifications, dimensions, application domain, and operating parameters.",
    badgeClass: "badge-warning",
  },
  NO_CONFIDENT_MATCH: {
    key: "NO_CONFIDENT_MATCH",
    label: "No Confident Match",
    explanation: "No indexed standard in the CED + ETD knowledge graph met technical applicability thresholds.",
    severity: "neutral",
    primaryAllowed: false,
    reviewExpected: false,
    nextAction: "Verify product terminology or consult engineering standards specialist for alternative classification.",
    badgeClass: "badge-secondary",
  },
  STANDARD_DATA_UNAVAILABLE: {
    key: "STANDARD_DATA_UNAVAILABLE",
    label: "Standard Data Unavailable",
    explanation: "Standard candidate was identified by designation but scope or lifecycle data is currently unavailable in index.",
    severity: "warning",
    primaryAllowed: false,
    reviewExpected: true,
    nextAction: "Consult official Bureau of Indian Standards portal or current standards catalog for latest edition.",
    badgeClass: "badge-warning",
  },
  OUTSIDE_PROTOTYPE_COVERAGE: {
    key: "OUTSIDE_PROTOTYPE_COVERAGE",
    label: "Outside Current CED + ETD Coverage",
    explanation: "This query belongs to a domain outside the current Civil Engineering (CED) and Electrotechnical (ETD) prototype scope.",
    severity: "neutral",
    primaryAllowed: false,
    reviewExpected: false,
    nextAction: "Review query against CED (Civil) and ETD (Electrical) scope; other BIS departments are planned for future releases.",
    badgeClass: "badge-secondary",
  },
  EXPERT_REVIEW_REQUIRED: {
    key: "EXPERT_REVIEW_REQUIRED",
    label: "Expert Review Required",
    explanation: "Potentially relevant candidate standard exists, but incomplete evidence or scope ambiguity prevents automatic recommendation.",
    severity: "warning",
    primaryAllowed: false,
    reviewExpected: true,
    nextAction: "Engineering expert review is required to verify standard applicability and compliance against tender requirements.",
    badgeClass: "badge-warning",
  },
  CLARIFICATION_REQUIRED: {
    key: "CLARIFICATION_REQUIRED",
    label: "Clarification Required",
    explanation: "Critical procurement discriminators are missing or ambiguous; clarification needed to distinguish candidates.",
    severity: "warning",
    primaryAllowed: false,
    reviewExpected: true,
    nextAction: "Answer the specific clarification questions indicated below to proceed with recommendation.",
    badgeClass: "badge-warning",
  },
  CONTRADICTORY_SPECIFICATIONS: {
    key: "CONTRADICTORY_SPECIFICATIONS",
    label: "Contradictory Specifications",
    explanation: "Specification contains mutually contradictory technical requirements (e.g. cross-domain or conflicting ratings).",
    severity: "danger",
    primaryAllowed: false,
    reviewExpected: false,
    nextAction: "Resolve conflicting technical parameters in the procurement specification before seeking standards recommendation.",
    badgeClass: "badge-danger",
  },
};

/**
 * Returns configuration metadata for a given decision state string.
 * Gracefully handles unknown or unverified states.
 */
export function getDecisionStateConfig(stateStr) {
  if (!stateStr) {
    return {
      key: "UNKNOWN",
      label: "Unknown Decision State",
      explanation: "Decision state not verified by backend.",
      severity: "neutral",
      primaryAllowed: false,
      reviewExpected: false,
      nextAction: "Verify backend response.",
      badgeClass: "badge-secondary",
    };
  }
  return DECISION_STATES[stateStr] || {
    key: stateStr,
    label: stateStr.replace(/_/g, " "),
    explanation: "Decision state reported by engine.",
    severity: "neutral",
    primaryAllowed: false,
    reviewExpected: false,
    nextAction: "Review recommendation details.",
    badgeClass: "badge-secondary",
  };
}
