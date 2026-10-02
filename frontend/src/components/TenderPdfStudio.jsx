import React, { useState } from 'react';
import { uploadTenderPdf, batchRecommend } from '../api';

const SAMPLE_TENDERS = [
  {
    name: "NTPC_Power_Distribution_Feeder_Package_2026.pdf",
    authority: "National Thermal Power Corporation (NTPC)",
    tenderId: "NIT-2026-NTPC-ELEC-088",
    pages: 34,
    date: "2026-08-20",
    clauses: [
      {
        item_id: "ITEM_001",
        clause_reference: "Section 3.1 - Schedule of Quantities Sl. 1",
        clause_type: "TECHNICAL_PROCUREMENT",
        is_technical: true,
        raw_text: "Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables conforming to standard specifications with outer extruded PVC sheathing.",
        page_number: 12,
        domain: "Electrotechnical (ETD)",
        extracted_entities: { product: "Power Cable", voltage: "1.1 kV", material: "XLPE", conductor: "Aluminium 240 sq mm" },
        baseline_recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 7098 (Part 1):1988",
          title: "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables - Specification: Part 1 For Working Voltages up to and Including 1100 V",
          department: "ETD",
          lifecycle_state: "VERIFIED_ACTIVE",
          is_mandatory_qco: true,
          regulatory_order: "Wires and Cables (Quality Control) Order, 2024",
          gazette_reference: "S.O. 1234(E)",
          confidence_score: 0.98,
        },
        recommendation: null,
        status: "PENDING_REVIEW",
      },
      {
        item_id: "ITEM_002",
        clause_reference: "Section 3.2 - Schedule of Quantities Sl. 2",
        clause_type: "TECHNICAL_PROCUREMENT",
        is_technical: true,
        raw_text: "Centrifugally cast (spun) iron pressure pipes for water supply mains, Class LA, nominal diameter 300 mm with flexible rubber push-on joints.",
        page_number: 15,
        domain: "Civil Engineering (CED)",
        extracted_entities: { product: "Spun Iron Pressure Pipes", material: "Cast Iron", dimensions: "DN 300 mm", grade: "Class LA" },
        baseline_recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 1536:2001",
          title: "Centrifugally Cast (Spun) Iron Pressure Pipes for Water, Gas and Sewage",
          department: "CED",
          lifecycle_state: "VERIFIED_ACTIVE",
          is_mandatory_qco: true,
          regulatory_order: "Cast Iron Products (Quality Control) Order, 2023",
          gazette_reference: "S.O. 4567(E)",
          confidence_score: 0.95,
        },
        recommendation: null,
        status: "PENDING_REVIEW",
      },
      {
        item_id: "ITEM_003",
        clause_reference: "Section 4.1 - Technical Specifications Cl. 7",
        clause_type: "TECHNICAL_PROCUREMENT",
        is_technical: true,
        raw_text: "Indoor type low voltage switchgear and controlgear assemblies for auxiliary AC distribution rated up to 1000 V AC.",
        page_number: 22,
        domain: "Electrotechnical (ETD)",
        extracted_entities: { product: "Switchgear Assembly", voltage: "1000 V AC", installation: "Indoor" },
        baseline_recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS/IEC 61439 (Part 1 & 2):2011",
          title: "Low-voltage Switchgear and Controlgear Assemblies: Part 1 General rules / Part 2 Power switchgear and controlgear assemblies",
          department: "ETD",
          lifecycle_state: "VERIFIED_ACTIVE",
          is_mandatory_qco: true,
          regulatory_order: "Low-Voltage Switchgear and Controlgear (Quality Control) Order, 2020",
          gazette_reference: "S.O. 3942(E)",
          confidence_score: 0.92,
        },
        recommendation: null,
        status: "PENDING_REVIEW",
      },
      {
        item_id: "ITEM_004",
        clause_reference: "Section 5.3 - Substation Package",
        clause_type: "TECHNICAL_PROCUREMENT",
        is_technical: true,
        raw_text: "Distribution transformers 11 kV / 433 V, 500 kVA outdoor type oil immersed conforming to IS 1180:1989.",
        page_number: 28,
        domain: "Electrotechnical (ETD)",
        cited_standard: "IS 1180:1989",
        extracted_entities: { product: "Distribution Transformer", voltage: "11 kV / 433 V", cited_standard: "IS 1180:1989" },
        baseline_recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 1180 (Part 1):2014",
          title: "Outdoor Type Oil Immersed Distribution Transformers up to and Including 2500 kVA, 33 kV",
          department: "ETD",
          lifecycle_state: "SUPERSEDED_IN_TENDER",
          lifecycle: {
            is_superseded: true,
            original_candidate: "IS 1180:1989",
            superseding_edition: "IS 1180 (Part 1):2014",
            transition_notes: "IS 1180:1989 was withdrawn and superseded by IS 1180 (Part 1):2014 with mandatory BEE star labeling."
          },
          is_mandatory_qco: true,
          regulatory_order: "Distribution Transformers (Quality Control) Order, 2023",
          confidence_score: 0.99,
        },
        recommendation: null,
        status: "PENDING_REVIEW",
      },
      {
        item_id: "ITEM_005",
        clause_reference: "Section 1.4 - Commercial Conditions Cl. 12",
        clause_type: "ADMINISTRATIVE_COMMERCIAL",
        is_technical: false,
        raw_text: "Earnest Money Deposit (EMD) of INR 5,00,000 to be submitted in the form of Bank Guarantee from any scheduled commercial bank valid for 180 days from bid closing date.",
        page_number: 5,
        domain: "Commercial / Legal",
        extracted_entities: { financial_guarantee: "EMD INR 5,00,000", validity: "180 days" },
        recommendation: null,
        status: "EXCLUDED_ADMINISTRATIVE",
      },
      {
        item_id: "ITEM_006",
        clause_reference: "Section 1.7 - General Conditions of Contract Cl. 18",
        clause_type: "ADMINISTRATIVE_COMMERCIAL",
        is_technical: false,
        raw_text: "Liquidated damages for delayed delivery will be levied at the rate of 0.5% per week of delay or part thereof, subject to a maximum ceiling of 10% of total contract value.",
        page_number: 8,
        domain: "Commercial / Legal",
        extracted_entities: { penalty_rate: "0.5% per week", max_penalty: "10% of contract value" },
        recommendation: null,
        status: "EXCLUDED_ADMINISTRATIVE",
      },
    ],
  },
];

export default function TenderPdfStudio({ evaluationDate }) {
  // P4.1: Clean initial state — docData starts null
  const [docData, setDocData] = useState(null);
  const [activeView, setActiveView] = useState('workbench'); // 'workbench' | 'audit'
  const [selectedItems, setSelectedItems] = useState([]);
  const [activeClause, setActiveClause] = useState(null);
  const [clauseFilter, setClauseFilter] = useState('all'); // 'all' | 'technical' | 'administrative'
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationFeedback, setVerificationFeedback] = useState(null);

  // File Upload with Size & Format Guards (P4.4)
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side PDF limit guard (20 MB)
    if (file.size > 20 * 1024 * 1024) {
      setUploadError(`PDF file (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum allowed size of 20 MB.`);
      return;
    }

    setUploading(true);
    setUploadError(null);
    setVerificationFeedback(null);

    try {
      // auto_verify is false (P4.2) so user can review and select clauses before running verification
      const parsed = await uploadTenderPdf(file, evaluationDate, false);
      const clauses = (parsed.clauses || []).map((c, idx) => ({
        ...c,
        item_id: c.item_id || `ITEM_${String(idx + 1).padStart(3, '0')}`,
        status: c.is_technical !== false ? 'PENDING_REVIEW' : 'EXCLUDED_ADMINISTRATIVE',
        recommendation: null,
      }));

      const newDoc = { ...parsed, clauses };
      setDocData(newDoc);

      if (clauses.length > 0) {
        setActiveClause(clauses[0]);
        // Pre-select technical clauses by default for officer review
        const techIds = clauses.filter(c => c.is_technical !== false).map(c => c.item_id);
        setSelectedItems(techIds.length > 0 ? techIds : clauses.map(c => c.item_id));
      }

      setVerificationFeedback({
        type: "success",
        message: `Extracted ${clauses.length} clauses (${clauses.filter(c => c.is_technical !== false).length} technical specifications). Select clauses and click 'Review & Analyze' to verify.`,
      });
    } catch (err) {
      console.error("PDF upload error:", err);
      setUploadError(err.message || "Failed to process PDF tender file.");
    } finally {
      setUploading(false);
    }
  };

  // Load sample demonstration tender (with live unverified state or precomputed baseline)
  const loadSampleTender = (withBaseline = false) => {
    const sample = SAMPLE_TENDERS[0];
    const clauses = sample.clauses.map(c => {
      if (withBaseline && c.baseline_recommendation) {
        const isSuperseded = c.baseline_recommendation.lifecycle_state === 'SUPERSEDED_IN_TENDER';
        return {
          ...c,
          recommendation: c.baseline_recommendation,
          status: isSuperseded ? 'SUPERSEDED_ALERT' : 'VERIFIED',
        };
      }
      return {
        ...c,
        recommendation: null,
        status: c.is_technical !== false ? 'PENDING_REVIEW' : 'EXCLUDED_ADMINISTRATIVE',
      };
    });

    const doc = {
      ...sample,
      filename: sample.name,
      page_count: sample.pages,
      is_synthetic_demo: true,
      tender_metadata: {
        issuing_authority: sample.authority,
        tender_id: sample.tenderId,
        publication_date: sample.date,
      },
      clauses,
    };

    setDocData(doc);
    setActiveClause(clauses[0]);
    setSelectedItems(clauses.filter(c => c.is_technical !== false).map(c => c.item_id));
    setUploadError(null);
    setVerificationFeedback({
      type: "success",
      message: withBaseline
        ? "Demonstration tender loaded with pre-computed baseline analysis."
        : "Demonstration tender loaded. Technical specifications selected for analysis.",
    });
  };

  const handleResetDocument = () => {
    setDocData(null);
    setSelectedItems([]);
    setActiveClause(null);
    setVerificationFeedback(null);
    setUploadError(null);
  };

  const toggleSelectItem = (itemId) => {
    setSelectedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    );
  };

  const selectAllFiltered = () => {
    const currentFiltered = filteredClauses.map(c => c.item_id);
    const allSelected = currentFiltered.every(id => selectedItems.includes(id));
    if (allSelected) {
      setSelectedItems(prev => prev.filter(id => !currentFiltered.includes(id)));
    } else {
      setSelectedItems(prev => Array.from(new Set([...prev, ...currentFiltered])));
    }
  };

  // P4.2 & P4.3: Review & Analyze Selected Clauses — Preserves full backend result
  const handleReviewAndAnalyzeSelected = async () => {
    if (selectedItems.length === 0) {
      alert("Please select at least one clause to analyze.");
      return;
    }

    const itemsToRun = (docData.clauses || []).filter(c => selectedItems.includes(c.item_id));
    setIsVerifying(true);
    setVerificationFeedback(null);

    try {
      const res = await batchRecommend(itemsToRun, evaluationDate);
      const resultsMap = new Map((res.results || []).map(r => [r.item_id, r]));

      setDocData(prev => {
        const updatedClauses = (prev.clauses || []).map(cl => {
          if (resultsMap.has(cl.item_id)) {
            const r = resultsMap.get(cl.item_id);
            const primary = r.primary_recommendation;
            const review = r.review_candidate;
            const life = r.lifecycle || primary?.lifecycle || {};
            const reg = r.regulatory || primary?.regulatory || {};
            const citationCheck = r.citation_lifecycle_check;
            const isContradictory = r.decision_state === 'CONTRADICTORY_SPECIFICATIONS';
            const isSuperseded = citationCheck
              ? (citationCheck.state === 'VERIFIED_SUPERSEDED' || citationCheck.state === 'VERIFIED_WITHDRAWN')
              : (life.lifecycle_state === 'VERIFIED_SUPERSEDED' || life.is_superseded === true);

            // PS 26108 Section 27: Retain full backend analysis result per clause
            return {
              ...cl,
              analysis: r,
              backend_result: r,
              decision_state: r.decision_state || (primary ? "PRIMARY_RECOMMENDATION_AVAILABLE" : (review ? "EXPERT_REVIEW_REQUIRED" : "INSUFFICIENT_INFORMATION")),
              contradiction_details: r.contradictions?.[0] || r.contradiction_details || null,
              clarification_prompts: r.clarifications_needed || r.clarification_prompts || [],
              citation_lifecycle_check: citationCheck,
              recommendation: primary ? {
                decision_state: r.decision_state,
                designation: primary.standard_designation || primary.designation,
                title: primary.title,
                department: primary.department || "NOT_VERIFIED",
                standard_role: primary.standard_role,
                lifecycle_state: life.lifecycle_state || "LIFECYCLE_UNKNOWN",
                lifecycle: life,
                is_mandatory_qco: reg.state === "MANDATORY_CONFIRMED" || reg.is_mandatory === true,
                regulatory_state: reg.state || reg.regulatory_state || "NOT_VERIFIED_IN_CURRENT_CORPUS",
                regulatory: reg,
                confidence_score: primary.confidence_score ?? null,
                evidence_gaps: primary.evidence_gaps || [],
                allied_standards: r.allied_standards || [],
                alternatives: r.candidate_recommendations || r.alternatives || [],
                is_review_candidate: false,
              } : (review ? {
                decision_state: r.decision_state,
                designation: review.standard_designation || review.designation,
                title: review.title,
                department: review.department || "NOT_VERIFIED",
                standard_role: review.standard_role,
                lifecycle_state: life.lifecycle_state || "LIFECYCLE_UNKNOWN",
                lifecycle: life,
                is_mandatory_qco: reg.state === "MANDATORY_CONFIRMED" || reg.is_mandatory === true,
                regulatory_state: reg.state || reg.regulatory_state || "NOT_VERIFIED_IN_CURRENT_CORPUS",
                regulatory: reg,
                confidence_score: review.confidence_score ?? null,
                evidence_gaps: review.evidence_gaps || [],
                allied_standards: r.allied_standards || [],
                alternatives: r.candidate_recommendations || r.alternatives || [],
                is_review_candidate: true,
              } : null),
              status: isContradictory ? "CONTRADICTORY" : (isSuperseded ? "SUPERSEDED_ALERT" : (primary ? "RECOMMENDATION_AVAILABLE" : (review ? "REVIEW_NEEDED" : "UNRESOLVED"))),
            };
          }
          return cl;
        });

        // Update activeClause reference if it was modified
        if (activeClause) {
          const fresh = updatedClauses.find(c => c.item_id === activeClause.item_id);
          if (fresh) setActiveClause(fresh);
        }

        return { ...prev, clauses: updatedClauses };
      });

      setVerificationFeedback({
        type: "success",
        message: `Successfully analyzed ${itemsToRun.length} selected specifications against CED + ETD standards graph.`,
      });
    } catch (err) {
      console.error("Batch verification failed:", err);
      setVerificationFeedback({
        type: "error",
        message: err.message || "Batch verification failed. Ensure backend API is active.",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  // Action: Analyze All Technical Clauses
  const handleAnalyzeAllTechnical = async () => {
    const techItems = (docData.clauses || []).filter(c => c.is_technical !== false);
    if (techItems.length === 0) {
      alert("No technical specifications found in this document.");
      return;
    }

    setSelectedItems(techItems.map(c => c.item_id));
    setIsVerifying(true);
    setVerificationFeedback(null);

    try {
      const res = await batchRecommend(techItems, evaluationDate);
      const resultsMap = new Map((res.results || []).map(r => [r.item_id, r]));

      setDocData(prev => {
        const updatedClauses = (prev.clauses || []).map(cl => {
          if (resultsMap.has(cl.item_id)) {
            const r = resultsMap.get(cl.item_id);
            const primary = r.primary_recommendation;
            const review = r.review_candidate;
            const life = r.lifecycle || primary?.lifecycle || {};
            const reg = r.regulatory || primary?.regulatory || {};
            const citationCheck = r.citation_lifecycle_check;
            const isContradictory = r.decision_state === 'CONTRADICTORY_SPECIFICATIONS';
            const isSuperseded = citationCheck
              ? (citationCheck.state === 'VERIFIED_SUPERSEDED' || citationCheck.state === 'VERIFIED_WITHDRAWN')
              : (life.lifecycle_state === 'VERIFIED_SUPERSEDED' || life.is_superseded === true);

            return {
              ...cl,
              analysis: r,
              backend_result: r,
              decision_state: r.decision_state || (primary ? "PRIMARY_RECOMMENDATION_AVAILABLE" : (review ? "EXPERT_REVIEW_REQUIRED" : "INSUFFICIENT_INFORMATION")),
              contradiction_details: r.contradictions?.[0] || r.contradiction_details || null,
              clarification_prompts: r.clarifications_needed || r.clarification_prompts || [],
              citation_lifecycle_check: citationCheck,
              recommendation: primary ? {
                decision_state: r.decision_state,
                designation: primary.standard_designation || primary.designation,
                title: primary.title,
                department: primary.department || "NOT_VERIFIED",
                standard_role: primary.standard_role,
                lifecycle_state: life.lifecycle_state || "LIFECYCLE_UNKNOWN",
                lifecycle: life,
                is_mandatory_qco: reg.state === "MANDATORY_CONFIRMED" || reg.is_mandatory === true,
                regulatory_state: reg.state || reg.regulatory_state || "NOT_VERIFIED_IN_CURRENT_CORPUS",
                regulatory: reg,
                confidence_score: primary.confidence_score ?? null,
                evidence_gaps: primary.evidence_gaps || [],
                allied_standards: r.allied_standards || [],
                alternatives: r.candidate_recommendations || r.alternatives || [],
                is_review_candidate: false,
              } : (review ? {
                decision_state: r.decision_state,
                designation: review.standard_designation || review.designation,
                title: review.title,
                department: review.department || "NOT_VERIFIED",
                standard_role: review.standard_role,
                lifecycle_state: life.lifecycle_state || "LIFECYCLE_UNKNOWN",
                lifecycle: life,
                is_mandatory_qco: reg.state === "MANDATORY_CONFIRMED" || reg.is_mandatory === true,
                regulatory_state: reg.state || reg.regulatory_state || "NOT_VERIFIED_IN_CURRENT_CORPUS",
                regulatory: reg,
                confidence_score: review.confidence_score ?? null,
                evidence_gaps: review.evidence_gaps || [],
                allied_standards: r.allied_standards || [],
                alternatives: r.candidate_recommendations || r.alternatives || [],
                is_review_candidate: true,
              } : null),
              status: isContradictory ? "CONTRADICTORY" : (isSuperseded ? "SUPERSEDED_ALERT" : (primary ? "RECOMMENDATION_AVAILABLE" : (review ? "REVIEW_NEEDED" : "UNRESOLVED"))),
            };
          }
          return cl;
        });

        if (activeClause) {
          const fresh = updatedClauses.find(c => c.item_id === activeClause.item_id);
          if (fresh) setActiveClause(fresh);
        }

        return { ...prev, clauses: updatedClauses };
      });

      setVerificationFeedback({
        type: "success",
        message: `Analyzed all ${techItems.length} technical specifications against CED + ETD catalog.`,
      });
    } catch (err) {
      console.error("Analyze all technical failed:", err);
      setVerificationFeedback({
        type: "error",
        message: err.message || "Failed to analyze technical clauses. Ensure backend API is active.",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  // Export JSON Assessment Dossier
  const exportComplianceReport = () => {
    if (!docData) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(docData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `STANDARDS_ASSESSMENT_${docData.tender_metadata?.tender_id || docData.tenderId || 'REPORT'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Export CSV Report
  const exportToCsv = () => {
    if (!docData) return;
    const headers = [
      "Item ID",
      "Clause Reference",
      "Classification",
      "Domain",
      "Page Number",
      "Specification Text",
      "Cited Standard",
      "Recommended Standard",
      "Standard Title",
      "Lifecycle State",
      "Mandatory QCO",
      "Regulatory Mandate Status",
      "Match Score",
      "Verification Status"
    ];

    const escapeCsv = (str) => {
      if (str === null || str === undefined) return '""';
      const clean = String(str).replace(/"/g, '""');
      return `"${clean}"`;
    };

    const rows = (docData.clauses || []).map(c => [
      escapeCsv(c.item_id),
      escapeCsv(c.clause_reference),
      escapeCsv(c.clause_type || (c.is_technical ? "TECHNICAL_PROCUREMENT" : "ADMINISTRATIVE_COMMERCIAL")),
      escapeCsv(c.domain),
      escapeCsv(c.page_number),
      escapeCsv(c.raw_text),
      escapeCsv(c.cited_standard || ""),
      escapeCsv(c.recommendation?.designation || "N/A"),
      escapeCsv(c.recommendation?.title || "N/A"),
      escapeCsv(c.recommendation?.lifecycle_state || "N/A"),
      escapeCsv(c.recommendation?.is_mandatory_qco ? "YES" : "NO"),
      escapeCsv(c.recommendation?.is_mandatory_qco ? (c.recommendation?.regulatory_order || "MANDATORY_QCO") : "NOT_MANDATED_IN_INDEXED_ORDERS"),
      escapeCsv(c.recommendation?.confidence_score ? c.recommendation.confidence_score.toFixed(2) : "N/A"),
      escapeCsv(c.status || "PENDING_REVIEW")
    ]);

    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `STANDARDS_ASSESSMENT_${docData.tender_metadata?.tender_id || docData.tenderId || 'REPORT'}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  // Calculations if docData exists
  const allClauses = docData?.clauses || [];
  const technicalClauses = allClauses.filter(c => c.is_technical !== false);
  const administrativeClauses = allClauses.filter(c => c.is_technical === false);

  const filteredClauses = allClauses.filter(c => {
    if (clauseFilter === 'technical') return c.is_technical !== false;
    if (clauseFilter === 'administrative') return c.is_technical === false;
    return true;
  });

  const totalItems = allClauses.length;
  const analyzedTechClauses = technicalClauses.filter(c => c.analysis || c.recommendation);
  const primaryAvailableCount = technicalClauses.filter(c => c.decision_state === 'PRIMARY_RECOMMENDATION_AVAILABLE' || c.status === 'RECOMMENDATION_AVAILABLE' || c.status === 'VERIFIED').length;
  const conditionalCount = technicalClauses.filter(c => c.decision_state === 'CONDITIONAL_RECOMMENDATION').length;
  const reviewRequiredCount = technicalClauses.filter(c => c.decision_state === 'EXPERT_REVIEW_REQUIRED' || c.status === 'REVIEW_NEEDED').length;
  const insufficientCount = technicalClauses.filter(c => c.decision_state === 'INSUFFICIENT_INFORMATION' || c.decision_state === 'CLARIFICATION_REQUIRED').length;
  const _outsideCoverageCount = technicalClauses.filter(c => c.decision_state === 'OUTSIDE_PROTOTYPE_COVERAGE').length;
  const contradictoryCount = technicalClauses.filter(c => c.status === 'CONTRADICTORY' || c.decision_state === 'CONTRADICTORY_SPECIFICATIONS').length;
  const supersededCount = technicalClauses.filter(c => c.status === 'SUPERSEDED_ALERT' || c.citation_lifecycle_check?.state === 'VERIFIED_SUPERSEDED').length;
  const _qcoCount = technicalClauses.filter(c => c.recommendation?.is_mandatory_qco).length;

  // Dynamic Red-Flag Findings (PS 26108 Section 28 & 43)
  const redFlags = allClauses.filter(c =>
    c.status === 'SUPERSEDED_ALERT' ||
    c.status === 'CONTRADICTORY' ||
    c.citation_lifecycle_check?.state === 'VERIFIED_SUPERSEDED' ||
    c.recommendation?.lifecycle_state === 'SUPERSEDED_IN_TENDER'
  );

  // ── Render Screen 1: Empty / Upload Landing Workspace ──
  if (!docData) {
    return (
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
        {/* Header */}
        <div className="w-full bg-white rounded-xl p-6 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 shadow-xs">
              <span className="material-symbols-outlined text-[24px]">picture_as_pdf</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900 font-display">
                Procurement Tender &amp; Schedule Analysis Studio
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload procurement tenders, extract technical clauses, and verify compliance against 6,082 indexed knowledge-graph nodes in CED + ETD
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 text-xs font-mono font-semibold">
              5-Step Officer Workflow
            </span>
          </div>
        </div>

        {/* 5-Step Process Pipeline */}
        <div className="w-full bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-4">
            Procedural Verification Pipeline
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            {[
              { num: "01", title: "Upload Tender PDF", desc: "Max 20 MB, up to 200 pages", icon: "upload_file", active: true },
              { num: "02", title: "Segment Clauses", desc: "Deterministic parser extracts items", icon: "segment", active: false },
              { num: "03", title: "Review & Select", desc: "Officer confirms technical items", icon: "checklist", active: false },
              { num: "04", title: "Verify Standards", desc: "Query graph, lifecycle & QCO gate", icon: "fact_check", active: false },
              { num: "05", title: "Assessment Dossier", desc: "Corrigenda alerts, CSV & JSON report", icon: "summarize", active: false },
            ].map((step, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-lg border flex flex-col gap-2 transition ${
                  step.active
                    ? "bg-blue-50/70 border-blue-200 text-blue-900"
                    : "bg-slate-50/50 border-slate-200/80 text-slate-600"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-400">{step.num}</span>
                  <span className={`material-symbols-outlined text-[18px] ${step.active ? "text-blue-600" : "text-slate-400"}`}>
                    {step.icon}
                  </span>
                </div>
                <div>
                  <div className="font-bold text-xs text-slate-900">{step.title}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{step.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Action Zone: Upload Dropzone & Sample Loader */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left: Drag & Drop Upload Zone (7 cols) */}
          <div className="lg:col-span-7 bg-white rounded-xl border-2 border-dashed border-slate-300 hover:border-blue-400 transition p-8 flex flex-col items-center justify-center text-center gap-4 shadow-xs">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100 shadow-xs">
              <span className="material-symbols-outlined text-[36px]">cloud_upload</span>
            </div>

            <div className="max-w-md">
              <h2 className="font-display font-bold text-base text-slate-900">
                Upload Procurement Document
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Upload tender notice, schedule of requirements, or technical specifications in PDF format.
              </p>
            </div>

            <label className="cursor-pointer px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-2 shadow-xs transition">
              <span className="material-symbols-outlined text-[18px]">file_open</span>
              <span>{uploading ? "Extracting Clauses..." : "Browse PDF File"}</span>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>

            <div className="text-[11px] font-mono text-slate-400 flex flex-wrap items-center justify-center gap-3">
              <span>Supports PDF up to 20 MB</span>
              <span>•</span>
              <span>Max 200 pages</span>
              <span>•</span>
              <span>Client &amp; Server Validated</span>
            </div>

            {uploadError && (
              <div className="w-full mt-2 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2 text-left">
                <span className="material-symbols-outlined text-[16px] shrink-0">error</span>
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {/* Right: Demonstration Tender Loader (5 cols) */}
          <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-emerald-700 font-semibold text-xs mb-2">
                <span className="material-symbols-outlined text-[18px]">verified</span>
                <span>Pre-loaded Demonstration Package</span>
              </div>
              <h3 className="font-display font-bold text-sm text-slate-900">
                NTPC Feeder Cable &amp; Transformer Package 2026
              </h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Representative public procurement NIT (34 pages) containing real-world electrical cables, spun iron pressure pipes, switchgear, and a deliberate superseded standard trap (IS 1180:1989).
              </p>

              <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Authority:</span>
                  <span className="text-slate-800 font-semibold">NTPC Limited</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tender ID:</span>
                  <span className="text-slate-800">NIT-2026-NTPC-ELEC-088</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Clauses:</span>
                  <span className="text-slate-800">4 Technical / 2 Commercial</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => loadSampleTender(false)}
                className="w-full px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-xs transition"
              >
                <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                <span>Load Sample for Live Analysis</span>
              </button>
              <button
                onClick={() => loadSampleTender(true)}
                className="w-full px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs flex items-center justify-center gap-1.5 border border-slate-200 transition"
              >
                <span className="material-symbols-outlined text-[15px]">preview</span>
                <span>Load with Precomputed Baseline</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Render Screen 2: Active Tender Analysis Workspace ──
  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* Synthetic Demo Mode Notice Banner (PS 26108 Section 42) */}
      {docData?.is_synthetic_demo && (
        <div className="w-full bg-amber-50 border border-amber-300 rounded-xl p-3.5 flex items-start sm:items-center gap-3 text-amber-950 text-xs shadow-xs">
          <span className="material-symbols-outlined text-amber-700 text-lg shrink-0">science</span>
          <div className="flex-1">
            <strong>DEMO DATA — SYNTHETIC / NON-AUTHORITATIVE:</strong>
            <span className="ml-1 text-amber-900">
              This sample tender package contains precomputed demonstration data for user interface evaluation. It is non-authoritative and does not represent live Bureau of Indian Standards compliance verification.
            </span>
          </div>
        </div>
      )}

      {/* Top Header & Breadcrumb with Document Info */}
      <div className="w-full bg-white rounded-xl p-4 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 shadow-xs">
            <span className="material-symbols-outlined text-[20px]">picture_as_pdf</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-slate-900 font-display">
                {docData.filename || docData.name}
              </h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                {docData.page_count || docData.pages} Pages
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Issuing Authority: <span className="font-semibold text-slate-700">{docData.tender_metadata?.issuing_authority || docData.authority}</span>
            </p>
          </div>
        </div>

        {/* View Switcher & Reset Button */}
        <div className="flex items-center gap-2">
          <div className="flex p-0.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-medium">
            <button
              onClick={() => setActiveView('workbench')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                activeView === 'workbench'
                  ? 'bg-white text-blue-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">view_kanban</span>
              <span>Workbench</span>
            </button>
            <button
              onClick={() => setActiveView('audit')}
              className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                activeView === 'audit'
                  ? 'bg-white text-emerald-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">fact_check</span>
              <span>Assessment Dossier</span>
            </button>
          </div>

          <button
            onClick={handleResetDocument}
            className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 text-xs font-medium shadow-xs transition flex items-center gap-1"
            title="Upload or load another tender document"
          >
            <span className="material-symbols-outlined text-[16px]">folder_open</span>
            <span>Switch Tender</span>
          </button>
        </div>
      </div>

      {/* Action / Error Banner */}
      {uploadError && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">error</span>
          <span>{uploadError}</span>
        </div>
      )}

      {verificationFeedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between gap-2 ${
            verificationFeedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">
              {verificationFeedback.type === 'success' ? 'check_circle' : 'error'}
            </span>
            <span>{verificationFeedback.message}</span>
          </div>
          <button
            onClick={() => setVerificationFeedback(null)}
            className="text-slate-400 hover:text-slate-600 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── VIEW A: INTERACTIVE CLAUSE WORKBENCH ── */}
      {activeView === 'workbench' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Clause Inspector & Grounded Text (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-5">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-blue-600">article</span>
                  <h3 className="font-display font-bold text-sm text-slate-900">
                    Clause Raw Text &amp; Scope Inspector
                  </h3>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                    activeClause?.is_technical !== false
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {activeClause?.is_technical !== false ? 'TECHNICAL' : 'ADMINISTRATIVE'}
                  </span>
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    {activeClause?.clause_reference || "Item"}
                  </span>
                </div>
              </div>

              {/* Raw Specification Text */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-800 leading-relaxed font-mono whitespace-pre-wrap">
                {activeClause?.raw_text}
              </div>

              {/* Extracted Parameters */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono">
                  Extracted Technical Attributes
                </span>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(activeClause?.extracted_entities || {}).map(([k, v], idx) => (
                    <div key={idx} className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-400 block uppercase font-mono">{k}</span>
                      <strong className="text-slate-800 font-medium">{String(v)}</strong>
                    </div>
                  ))}
                  {Object.keys(activeClause?.extracted_entities || {}).length === 0 && (
                    <div className="col-span-2 text-slate-400 text-xs italic">
                      No specific technical parameters extracted (Administrative/General Clause).
                    </div>
                  )}
                </div>
              </div>

              {/* Contradiction Alert if detected */}
              {activeClause?.status === 'CONTRADICTORY' && (
                <div className="p-3 rounded-lg bg-purple-50 border border-purple-200 flex flex-col gap-1 text-xs text-purple-900">
                  <div className="flex items-center gap-1.5 font-bold">
                    <span className="material-symbols-outlined text-[16px] text-purple-700">error</span>
                    <span>Contradictory Technical Specification</span>
                  </div>
                  <p className="text-[11px] text-purple-800 mt-0.5">
                    {activeClause?.contradiction_details?.description || "Incompatible standards or conflicting parameter requirements detected."}
                  </p>
                  {activeClause?.clarification_prompts?.length > 0 && (
                    <div className="mt-1 text-[11px] font-semibold">
                      Action Required: {activeClause.clarification_prompts[0]}
                    </div>
                  )}
                </div>
              )}

              {/* Recommended Standard Pill (P4.3: Full Backend Result Display) */}
              {activeClause?.recommendation ? (
                <div className="p-3.5 rounded-lg bg-emerald-50/70 border border-emerald-200 flex flex-col gap-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-mono font-bold text-emerald-800">
                      Authoritative Primary Standard
                    </span>
                    {activeClause.recommendation.standard_role && (
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold border border-emerald-200">
                        {activeClause.recommendation.standard_role}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      {activeClause.recommendation.designation}
                    </span>
                    {activeClause.recommendation.is_mandatory_qco ? (
                      <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-mono text-[10px] font-bold border border-amber-200">
                        QCO MANDATORY
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px]">
                        NOT MANDATED IN INDEXED ORDERS
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-700 line-clamp-2">
                    {activeClause.recommendation.title}
                  </p>

                  {/* Lifecycle transition warning if superseded */}
                  {activeClause.status === 'SUPERSEDED_ALERT' && (
                    <div className="p-2 rounded bg-rose-50 border border-rose-200 text-rose-800 text-[11px] leading-tight">
                      <strong>⚠ Superseded Standard Alert: </strong>
                      {activeClause.cited_standard ? `Tender cites ${activeClause.cited_standard}. ` : ''}
                      Current active edition is {activeClause.recommendation.designation}.
                    </div>
                  )}

                  {/* Match Score */}
                  <div className="flex items-center justify-between text-[11px] pt-1 border-t border-emerald-100 text-slate-500 font-mono">
                    <span>Match Score: {typeof activeClause.recommendation.confidence_score === 'number' ? activeClause.recommendation.confidence_score.toFixed(2) : "0.90"} (Uncalibrated)</span>
                    <span className="text-emerald-700 font-semibold">{activeClause.recommendation.lifecycle_state || "ACTIVE"}</span>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500 italic">
                  {activeClause?.is_technical === false
                    ? "Administrative/contractual clause — excluded from standards recommendation."
                    : "Standard verification pending. Select clause and click 'Review & Analyze Selected'."}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Line-Items Table & Actions (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
              {/* Filter Tabs & Top Controls */}
              <div className="p-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-3">
                {/* Filter Pills */}
                <div className="flex items-center gap-1.5 text-xs">
                  <button
                    onClick={() => setClauseFilter('all')}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      clauseFilter === 'all'
                        ? 'bg-white border border-slate-300 text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    All Clauses ({totalItems})
                  </button>
                  <button
                    onClick={() => setClauseFilter('technical')}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      clauseFilter === 'technical'
                        ? 'bg-blue-50 border border-blue-200 text-blue-800 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Technical Specifications ({technicalClauses.length})
                  </button>
                  <button
                    onClick={() => setClauseFilter('administrative')}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      clauseFilter === 'administrative'
                        ? 'bg-slate-200 border border-slate-300 text-slate-800 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Administrative ({administrativeClauses.length})
                  </button>
                </div>

                {/* Export Buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={exportToCsv}
                    className="px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium shadow-xs transition flex items-center gap-1"
                    title="Export table as CSV"
                  >
                    <span className="material-symbols-outlined text-[14px]">table_view</span>
                    <span>Export CSV</span>
                  </button>
                  <button
                    onClick={exportComplianceReport}
                    className="px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium shadow-xs transition flex items-center gap-1"
                    title="Export full JSON dossier"
                  >
                    <span className="material-symbols-outlined text-[14px]">download</span>
                    <span>Export JSON</span>
                  </button>
                </div>
              </div>

              {/* Selection Bar & Primary Action Buttons (P4.2) */}
              <div className="p-3 border-b border-slate-100 bg-white flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={selectAllFiltered}
                    className="text-xs font-semibold text-blue-700 hover:text-blue-900"
                  >
                    {filteredClauses.every(c => selectedItems.includes(c.item_id)) && filteredClauses.length > 0
                      ? "Deselect Filtered"
                      : "Select Filtered"}
                  </button>
                  <span className="text-slate-300">|</span>
                  <span className="text-xs text-slate-600 font-mono">
                    {selectedItems.length} of {totalItems} Selected
                  </span>
                </div>

                {/* Explicit Action Buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleReviewAndAnalyzeSelected}
                    disabled={isVerifying || selectedItems.length === 0}
                    className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium text-xs shadow-xs flex items-center gap-1.5 transition"
                  >
                    <span className={`material-symbols-outlined text-[16px] ${isVerifying ? 'animate-spin' : ''}`}>
                      {isVerifying ? 'refresh' : 'play_arrow'}
                    </span>
                    <span>Review &amp; Analyze Selected ({selectedItems.length})</span>
                  </button>
                  <button
                    onClick={handleAnalyzeAllTechnical}
                    disabled={isVerifying || technicalClauses.length === 0}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-800 font-medium text-xs border border-slate-200 shadow-xs flex items-center gap-1 transition"
                  >
                    <span className="material-symbols-outlined text-[15px]">fast_forward</span>
                    <span>Analyze All Technical ({technicalClauses.length})</span>
                  </button>
                </div>
              </div>

              {/* Clauses Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3 w-8">
                        <input
                          type="checkbox"
                          checked={filteredClauses.every(c => selectedItems.includes(c.item_id)) && filteredClauses.length > 0}
                          onChange={selectAllFiltered}
                          className="rounded text-blue-600 focus:ring-blue-500"
                        />
                      </th>
                      <th className="py-2.5 px-3">Item / Clause Ref</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Domain</th>
                      <th className="py-2.5 px-3">Recommended IS</th>
                      <th className="py-2.5 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredClauses.map((cl) => {
                      const isSelected = selectedItems.includes(cl.item_id);
                      const isActive = activeClause?.item_id === cl.item_id;
                      const isSuperseded = cl.status === 'SUPERSEDED_ALERT' || cl.recommendation?.lifecycle_state === 'SUPERSEDED_IN_TENDER';
                      const isContradictory = cl.status === 'CONTRADICTORY';
                      const isVerified = cl.status === 'VERIFIED';
                      const isAdmin = cl.is_technical === false;

                      return (
                        <tr
                          key={cl.item_id}
                          onClick={() => setActiveClause(cl)}
                          className={`cursor-pointer transition-colors ${
                            isActive ? 'bg-blue-50/60' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-2.5 px-3" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelectItem(cl.item_id)}
                              className="rounded text-blue-600 focus:ring-blue-500"
                            />
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="font-semibold text-slate-900">{cl.clause_reference}</div>
                            <div className="text-[11px] text-slate-500 line-clamp-1 max-w-[280px]">
                              {cl.raw_text}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded ${
                              isAdmin ? 'bg-slate-100 text-slate-600' : 'bg-blue-50 text-blue-700 border border-blue-100'
                            }`}>
                              {isAdmin ? 'ADMIN' : 'TECH'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                              {cl.domain}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                            {cl.recommendation?.designation || (isAdmin ? "—" : "Pending")}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {isContradictory ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                                ⚠ CONFLICT
                              </span>
                            ) : isSuperseded ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                ⚠ SUPERSEDED
                              </span>
                            ) : isVerified ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                ✓ VERIFIED
                              </span>
                            ) : isAdmin ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                                EXCLUDED
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                                PENDING
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── VIEW B: FULL-DOCUMENT STANDARDS ASSESSMENT DOSSIER ── */}
      {activeView === 'audit' && (
        <div className="flex flex-col gap-6">
          {/* Statutory Legal Notice Disclaimer Banner */}
          <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-900 text-xs leading-relaxed flex items-start gap-3 shadow-xs">
            <span className="material-symbols-outlined text-[20px] text-amber-700 shrink-0 mt-0.5">gavel</span>
            <div>
              <strong className="block text-xs font-bold uppercase tracking-wider text-amber-900 font-mono mb-0.5">
                Statutory Notice &amp; Legal Integrity Disclaimer
              </strong>
              <p>
                This assessment dossier is an AI-assisted procurement reference analysis generated by StandSpec AI against the indexed BIS standards corpus and regulatory evidence. <strong>It does not constitute official BIS product certification, ISI mark grant, or a statutory compliance certificate.</strong> All findings must be formally reviewed and ratified by the competent technical authority prior to tender finalization.
              </p>
            </div>
          </div>

          {/* Executive Metrics Cards (4 cards) — Neutral Operational Summary (PS 26108 Section 30) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">list_alt</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Clauses Analyzed</span>
                <span className="text-xl font-bold text-slate-900">
                  {analyzedTechClauses.length} of {technicalClauses.length} Tech
                </span>
                <span className="text-[11px] text-slate-500 block">
                  {administrativeClauses.length} Administrative Excluded
                </span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">fact_check</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Recommendations Available</span>
                <span className="text-xl font-bold text-emerald-700">
                  {primaryAvailableCount + conditionalCount} Standards
                </span>
                <span className="text-[11px] text-emerald-800 block">
                  {primaryAvailableCount} Primary • {conditionalCount} Conditional
                </span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">engineering</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Review &amp; Clarification</span>
                <span className="text-xl font-bold text-amber-700">
                  {reviewRequiredCount + insufficientCount} Items
                </span>
                <span className="text-[11px] text-slate-500 block">
                  {reviewRequiredCount} Expert Review • {insufficientCount} Insufficient Info
                </span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">warning</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Superseded / Conflicts</span>
                <span className="text-xl font-bold text-rose-700">
                  {supersededCount + contradictoryCount} Discrepancies
                </span>
                <span className="text-[11px] text-rose-800 block">
                  {supersededCount} Superseded • {contradictoryCount} Contradictory
                </span>
              </div>
            </div>
          </div>

          {/* Dynamic Red-Flag Alerts Section */}
          <div className="bg-white rounded-xl border border-rose-200 p-5 shadow-xs flex flex-col gap-3">
            <div className="flex items-center gap-2 text-rose-800">
              <span className="material-symbols-outlined text-[20px]">report</span>
              <h3 className="font-display font-bold text-sm">
                Technical Discrepancies &amp; Superseded Standard Alerts
              </h3>
            </div>

            {redFlags.length > 0 ? (
              redFlags.map((cl, idx) => (
                <div key={idx} className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900 leading-relaxed flex items-start gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-rose-600 mt-0.5">cancel</span>
                  <div>
                    <strong className="block text-sm font-semibold">
                      {cl.status === 'CONTRADICTORY'
                        ? `Contradictory Technical Specification in ${cl.clause_reference}`
                        : `Tender Cites Superseded Standard: ${cl.cited_standard || cl.recommendation?.designation} in ${cl.clause_reference} (Page ${cl.page_number || 'N/A'})`
                      }
                    </strong>
                    <p className="mt-1">
                      {cl.status === 'CONTRADICTORY'
                        ? (cl.contradiction_details?.description || "Incompatible standards or conflicting parameter requirements detected in tender clause.")
                        : `The tender document references a withdrawn or superseded standard edition. The current active Indian Standard is ${cl.recommendation?.designation}. Bids quoting withdrawn editions may reference obsolete technical criteria.`
                      }
                    </p>
                    <div className="mt-2 text-rose-800 font-semibold">
                      Recommended Action: {cl.status === 'CONTRADICTORY'
                        ? `Clarify conflicting parameters: ${cl.clarification_prompts?.[0] || 'Clarify exact specification required.'}`
                        : `Verify procurement specification against current active edition ${cl.recommendation?.designation || 'in the standards catalog'}.`
                      }
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
                <span>No statutory discrepancies or superseded standard citations detected among analyzed clauses.</span>
              </div>
            )}
          </div>

          {/* Full Audit Grid */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-sm text-slate-900">
                Consolidated Standards Assessment Grid
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={exportToCsv}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium shadow-xs flex items-center gap-1 transition"
                >
                  <span className="material-symbols-outlined text-[16px]">table_view</span>
                  <span>Export Grid (CSV)</span>
                </button>
                <button
                  onClick={exportComplianceReport}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs shadow-xs flex items-center gap-1 transition"
                >
                  <span className="material-symbols-outlined text-[16px]">download</span>
                  <span>Export Dossier (JSON)</span>
                </button>
              </div>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Sl. No.</th>
                    <th className="py-2.5 px-3">Tender Specification Demand</th>
                    <th className="py-2.5 px-3">Harmonized BIS Standard</th>
                    <th className="py-2.5 px-3">Lifecycle State</th>
                    <th className="py-2.5 px-3">Mandatory QCO</th>
                    <th className="py-2.5 px-3 text-right">Compliance Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {technicalClauses.map((cl, i) => (
                    <tr key={i} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-mono font-semibold">{i + 1}</td>
                      <td className="py-2.5 px-3 font-mono text-[11px] max-w-xs">{cl.raw_text}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                        {cl.recommendation?.designation || "Pending Verification"}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {cl.status === 'CONTRADICTORY' ? (
                          <span className="text-purple-700 font-bold">CONFLICT DETECTED</span>
                        ) : cl.status === 'SUPERSEDED_ALERT' ? (
                          <span className="text-rose-600 font-bold">SUPERSEDED (Update Req)</span>
                        ) : cl.status === 'VERIFIED' ? (
                          <span className="text-emerald-700 font-bold">ACTIVE (Valid)</span>
                        ) : (
                          <span className="text-amber-700 font-medium">PENDING</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {cl.recommendation?.is_mandatory_qco ? (
                          <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono text-[10px] font-bold">
                            MANDATORY (QCO)
                          </span>
                        ) : (
                          <span className="text-slate-500 font-mono text-[10px]">
                            NOT MANDATED IN INDEXED ORDERS
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium">
                        {cl.status === 'CONTRADICTORY' ? (
                          <span className="text-purple-700 font-bold">Clarification Addendum</span>
                        ) : cl.status === 'SUPERSEDED_ALERT' ? (
                          <span className="text-rose-700 font-bold">Issue Corrigendum</span>
                        ) : cl.status === 'VERIFIED' ? (
                          <span className="text-emerald-700">Conforming</span>
                        ) : (
                          <span className="text-slate-500">Awaiting Verification</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
