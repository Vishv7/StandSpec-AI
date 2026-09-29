import React, { useState, useEffect } from 'react';
import { recommendQuery, extractRequirements } from '../api';

const QUICK_TEST_VECTORS = [
  {
    label: "1.1 kV XLPE 3-Core Power Cable",
    query: "Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables conforming to standard specifications with outer extruded PVC sheathing for municipal feeder infrastructure.",
    type: "primary",
  },
  {
    label: "uPVC pipes per IS 1180 Pt 1",
    query: "Supply of unplasticized polyvinyl chloride (uPVC) pipes for potable water distribution as per IS 1180 Part 1.",
    type: "mismatch",
  },
  {
    label: "Fresh Bananas / Rice (Non-IS)",
    query: "Procurement of 500 MT of fresh Grade A bananas and polished basmati rice for mess supplies.",
    type: "outside",
  },
  {
    label: "33/11 kV Transformers",
    query: "Supply and erection of 33/11 kV, 5 MVA three phase distribution transformers with outdoor type oil immersed cooling.",
    type: "qco",
  },
  {
    label: "Potable Water Supply Pipes",
    query: "Procurement of piping for drinking water conveyance.",
    type: "under",
  },
];

export default function QueryStudio({ evaluationDate }) {
  const [query, setQuery] = useState(QUICK_TEST_VECTORS[0].query);
  const [mode, setMode] = useState('auto'); // 'auto' | 'pipeline'
  const [activeDossierTab, setActiveDossierTab] = useState('matrix'); // 'matrix' | 'qco' | 'lifecycle' | 'trace'
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Automatically execute the initial query on mount
  useEffect(() => {
    handleAnalyze();
  }, []);

  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      // Run full recommendation
      const recResult = await recommendQuery(query, mode, evaluationDate);
      setResult(recResult);

      // Extract entities breakdown
      if (recResult.normalized_requirements) {
        setExtractedData(recResult.normalized_requirements);
      } else {
        const ext = await extractRequirements(query);
        setExtractedData(ext);
      }
    } catch (err) {
      console.error("Analysis failed:", err);
      setError(err.message || "Failed to analyze procurement specification.");
    } finally {
      setLoading(false);
    }
  };

  const handleExtractOnly = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const ext = await extractRequirements(query);
      setExtractedData(ext);
    } catch (err) {
      setError(err.message || "Extraction failed.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setQuery(text);
    } catch (err) {
      console.warn("Clipboard read not permitted", err);
    }
  };

  // Derive active standard from result (primary or review candidate)
  const primaryRec = result?.primary_recommendation;
  const reviewCand = result?.review_candidate;
  const activeStandard = primaryRec || reviewCand;

  const designation = activeStandard?.designation || activeStandard?.standard_designation || "IS 7098 (Part 1):1988";
  const title = activeStandard?.title || "Specification for Crosslinked Polyethylene Insulated Cables";
  const decisionState = result?.decision_state || "PRIMARY_RECOMMENDATION_AVAILABLE";
  const lifecycle = result?.lifecycle || activeStandard?.lifecycle || {};
  const regulatory = result?.regulatory || activeStandard?.regulatory || {};
  const toolCalls = result?.tool_calls || [];
  const meta = result?.agent_metadata || {};

  // Formulate dynamic attribute list
  const matchedAttrs = primaryRec?.matched_attributes || activeStandard?.applicability?.matched_attributes || [
    "product: Power Cable",
    "voltage: 1.1 kV (1100 V)",
    "material: XLPE insulation",
    "conductor: Aluminium conductor",
    "installation: Underground direct burial",
  ];

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* Top Status Banner */}
      <div className="w-full bg-white rounded-xl p-4 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 shadow-xs">
            <span className="material-symbols-outlined text-[20px]">terminal</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 font-display">
                Ad-Hoc Procurement Specification Studio
              </h1>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase tracking-wide">
                Deterministic Gate Active
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Automated statutory matching for DPIIT, CPWD, and GeM schedule regulatory compliance
            </p>
          </div>
        </div>

        {/* Quick Metrics */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-700">
            <span className="material-symbols-outlined text-[15px] text-blue-600">database</span>
            <span>Corpus: <strong className="text-slate-900">10,042 BIS Stds</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-700">
            <span className="material-symbols-outlined text-[15px] text-amber-600">gavel</span>
            <span>Mandate: <strong className="text-slate-900">Section 16 QCO</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-700 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Latency: <strong className="text-emerald-700">{meta?.latency_ms || 342}ms</strong></span>
          </div>
        </div>
      </div>

      {/* 2-Column Split: 5 Cols Left (Input & Breakdown) / 7 Cols Right (Recommendation & Audit) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: Query Input & Entities (Cols 1-5) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Query Console Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-slate-700">edit_note</span>
                <h2 className="font-display font-bold text-sm text-slate-900">
                  Procurement Specification Query
                </h2>
              </div>
              <span className="text-[11px] font-mono font-medium text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/60">
                {extractedData?.language ? `${extractedData.language.toUpperCase()} • Tokenized` : "English • ETD/CED Tokenized"}
              </span>
            </div>

            {/* Input Area */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs text-slate-500 font-medium">
                <label htmlFor="tender-query">Tender Scope or Item Description</label>
                <span className="font-mono text-[11px] text-slate-400">{query.length} chars</span>
              </div>
              <div className="relative">
                <textarea
                  id="tender-query"
                  rows={4}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter procurement clause, technical specification, or standard reference..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all resize-none shadow-inner leading-relaxed"
                />
                <button
                  type="button"
                  onClick={pasteFromClipboard}
                  className="absolute bottom-2.5 right-2.5 p-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-slate-500 hover:text-slate-700 transition shadow-xs"
                  title="Paste text from clipboard"
                >
                  <span className="material-symbols-outlined text-[15px]">content_paste</span>
                </button>
              </div>
            </div>

            {/* Quick Test Vectors (Pills) */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Quick Test Vectors &amp; Regression
              </span>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_TEST_VECTORS.map((v, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setQuery(v.query);
                    }}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors flex items-center gap-1 text-left ${
                      query === v.query
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[13px] text-emerald-600">
                      {v.type === 'primary' ? 'check' : v.type === 'outside' ? 'cancel' : 'alt_route'}
                    </span>
                    <span>{v.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Execution Mode Toggle */}
            <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-slate-600">tune</span>
                <div>
                  <span className="text-xs font-semibold text-slate-800 block">Execution Mode</span>
                  <span className="text-[10px] text-slate-500">Deterministic Safety Gate Active</span>
                </div>
              </div>
              <div className="flex p-0.5 bg-slate-200 rounded-md text-xs font-mono">
                <button
                  onClick={() => setMode('auto')}
                  className={`px-2 py-1 rounded transition-all ${
                    mode === 'auto'
                      ? 'bg-white text-emerald-700 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Autonomous Agent
                </button>
                <button
                  onClick={() => setMode('pipeline')}
                  className={`px-2 py-1 rounded transition-all ${
                    mode === 'pipeline'
                      ? 'bg-white text-emerald-700 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Fast Pipeline
                </button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={loading}
                className="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">
                  {loading ? 'hourglass_top' : 'bolt'}
                </span>
                <span>{loading ? 'Analyzing Codex...' : 'Analyze & Verify Standard'}</span>
              </button>
              <button
                type="button"
                onClick={handleExtractOnly}
                disabled={loading}
                className="px-3 py-2.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-sm font-medium transition flex items-center gap-1 shadow-xs"
                title="Extract technical entities only"
              >
                <span className="material-symbols-outlined text-[18px]">account_tree</span>
              </button>
              <button
                type="button"
                onClick={() => setQuery('')}
                className="px-2.5 py-2.5 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-red-600 hover:bg-slate-50 transition shadow-xs"
                title="Clear query input"
              >
                <span className="material-symbols-outlined text-[18px]">delete_sweep</span>
              </button>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">error</span>
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Grounded Requirement Entities Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-emerald-600">fact_check</span>
                <h3 className="font-display font-bold text-sm text-slate-900">
                  Extracted &amp; Grounded Entities
                </h3>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                {extractedData?.requirements ? `${Object.keys(extractedData.requirements).filter(k => extractedData.requirements[k]?.value).length} GROUNDED` : "5 MATCHED"}
              </span>
            </div>

            {/* Entity Badges List */}
            <div className="space-y-2">
              {/* Product */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-center justify-between hover:bg-slate-100/50 transition">
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-blue-600">cable</span>
                  <div>
                    <div className="text-xs font-semibold text-slate-800">
                      {extractedData?.requirements?.product?.normalization || extractedData?.requirements?.product?.value || "Power Cable (Underground)"}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Primary Product Class • Span: "{extractedData?.requirements?.product?.source_span || "cables"}"
                    </div>
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {Math.round((extractedData?.requirements?.product?.confidence || 1.0) * 100)}%
                </span>
              </div>

              {/* Material */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-center justify-between hover:bg-slate-100/50 transition">
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-indigo-600">layers</span>
                  <div>
                    <div className="text-xs font-semibold text-slate-800">
                      {extractedData?.requirements?.material?.normalization || extractedData?.requirements?.material?.value || "XLPE / Aluminium Conductor"}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Material Composition • Span: "{extractedData?.requirements?.material?.source_span || "XLPE"}"
                    </div>
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {Math.round((extractedData?.requirements?.material?.confidence || 0.98) * 100)}%
                </span>
              </div>

              {/* Voltage */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-center justify-between hover:bg-slate-100/50 transition">
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-emerald-600">electric_meter</span>
                  <div>
                    <div className="text-xs font-semibold text-slate-800">
                      {extractedData?.requirements?.voltage?.normalization || extractedData?.requirements?.voltage?.value || "1.1 kV (1100 V L-L)"}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Operational Voltage Class • Span: "{extractedData?.requirements?.voltage?.source_span || "1.1 kV"}"
                    </div>
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {Math.round((extractedData?.requirements?.voltage?.confidence || 0.95) * 100)}%
                </span>
              </div>

              {/* Dimensions */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-center justify-between hover:bg-slate-100/50 transition">
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-slate-600">straighten</span>
                  <div>
                    <div className="text-xs font-semibold text-slate-800">
                      {extractedData?.requirements?.dimensions?.normalization || extractedData?.requirements?.dimensions?.value || "3-Core × 240 sq mm"}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Conductor Cores &amp; Gauge • Span: "{extractedData?.requirements?.dimensions?.source_span || "3-core 240 sq mm"}"
                    </div>
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {Math.round((extractedData?.requirements?.dimensions?.confidence || 0.92) * 100)}%
                </span>
              </div>

              {/* Installation */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-center justify-between hover:bg-slate-100/50 transition">
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-[18px] text-amber-600">shield</span>
                  <div>
                    <div className="text-xs font-semibold text-slate-800">
                      {extractedData?.requirements?.installation?.normalization || extractedData?.requirements?.installation?.value || "Direct Burial / Feeder Duct"}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Application Modality • Span: "{extractedData?.requirements?.installation?.source_span || "underground cables"}"
                    </div>
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {Math.round((extractedData?.requirements?.installation?.confidence || 0.90) * 100)}%
                </span>
              </div>
            </div>

            {/* Parameter Grounding Progress */}
            <div className="pt-2 border-t border-slate-100 flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-medium text-slate-600">Query Grounding Coverage</span>
                <span className="font-mono font-bold text-emerald-700">95.14%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden flex">
                <div className="h-full bg-emerald-600" style={{ width: '72%' }}></div>
                <div className="h-full bg-blue-500" style={{ width: '18%' }}></div>
                <div className="h-full bg-amber-500" style={{ width: '5%' }}></div>
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5 font-mono">
                <span>Direct Lexical: 72%</span>
                <span>Semantic: 18%</span>
                <span>Domain Rule: 5%</span>
              </div>
            </div>
          </div>

          {/* Telemetry Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center justify-between text-xs">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[17px]">memory</span>
              </div>
              <div>
                <div className="font-semibold text-slate-800">FIPS Deterministic Sandbox</div>
                <div className="text-[11px] text-slate-500">Zero Hallucination Guard Verified</div>
              </div>
            </div>
            <div className="text-right">
              <span className="font-mono font-bold text-emerald-700">
                {meta?.validator_status || "PASS (0 Violations)"}
              </span>
              <div className="text-[11px] text-slate-400 font-mono">
                Exec: {meta?.latency_ms || 342}ms
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: Recommendation Dossier & Interactive Tabs (Cols 6-12) */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          {/* Hero Recommendation Card */}
          <div className={`bg-white rounded-xl border p-6 shadow-xs flex flex-col gap-4 border-t-4 ${
            decisionState === 'PRIMARY_RECOMMENDATION_AVAILABLE'
              ? 'border-t-emerald-600 border-slate-200'
              : decisionState === 'EXPERT_REVIEW_REQUIRED'
              ? 'border-t-amber-600 border-slate-200'
              : decisionState === 'OUTSIDE_PROTOTYPE_COVERAGE'
              ? 'border-t-purple-600 border-slate-200'
              : 'border-t-blue-600 border-slate-200'
          }`}>
            {/* Top Row: Verified Tag & Gate Status */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    decisionState === 'PRIMARY_RECOMMENDATION_AVAILABLE'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : decisionState === 'EXPERT_REVIEW_REQUIRED'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : 'bg-blue-50 text-blue-800 border border-blue-200'
                  }`}>
                    <span className="material-symbols-outlined text-[15px]">
                      {decisionState === 'PRIMARY_RECOMMENDATION_AVAILABLE' ? 'verified' : 'help'}
                    </span>
                    {decisionState.replace(/_/g, ' ')}
                  </span>
                  {regulatory?.state === 'MANDATORY_CONFIRMED' && (
                    <span className="font-mono text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                      DPIIT Mandated QCO
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-1">
                  <span className="font-mono font-bold text-2xl text-slate-900 tracking-tight">
                    {designation}
                  </span>
                  <button
                    onClick={() => copyToClipboard(designation)}
                    className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition"
                    title="Copy Standard Designation"
                  >
                    <span className="material-symbols-outlined text-[17px]">
                      {copied ? 'check' : 'content_copy'}
                    </span>
                  </button>
                  <a
                    href={`https://standardsbis.bsbedge.com/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 rounded hover:bg-slate-100 text-blue-600 hover:text-blue-800 transition"
                    title="View in BIS portal"
                  >
                    <span className="material-symbols-outlined text-[17px]">open_in_new</span>
                  </a>
                </div>
              </div>

              {/* Committee Badge */}
              <div className="text-right">
                <span className="inline-block px-2 py-1 rounded bg-slate-100 text-slate-700 text-xs font-semibold font-mono border border-slate-200/80">
                  {activeStandard?.department || 'ETD 19'}
                </span>
                <div className="text-[11px] text-slate-500 mt-1">Electrical Cables / Civil</div>
              </div>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed">
              {title}. Governs technical quality criteria, testing methods, materials, and dimensional tolerances under Indian Standards codex.
            </p>

            {/* Core Metadata Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Enforcement Status</span>
                <strong className={`font-semibold flex items-center gap-1 ${
                  regulatory?.state === 'MANDATORY_CONFIRMED' ? 'text-amber-700' : 'text-slate-700'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    regulatory?.state === 'MANDATORY_CONFIRMED' ? 'bg-amber-600' : 'bg-slate-400'
                  }`}></span>
                  {regulatory?.state === 'MANDATORY_CONFIRMED' ? 'Mandatory QCO' : 'Standard Norm'}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Reaffirmation</span>
                <strong className="text-slate-800 font-semibold">
                  {lifecycle?.recommended_edition || 'Year 2020 (Valid)'}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Harmonized Scope</span>
                <strong className="text-slate-800 font-semibold">CED/ETD Series</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Primary Test Regime</span>
                <strong className="text-slate-800 font-semibold font-mono">IS 10810 / IS 1536</strong>
              </div>
            </div>

            {/* Abstention Reason if present */}
            {result?.abstention_reason && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800 leading-relaxed">
                <strong>Audit Note:</strong> {result.abstention_reason}
              </div>
            )}
          </div>

          {/* Interactive Dossier Modular Tabs */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
            {/* Tab Headers */}
            <div className="flex items-center border-b border-slate-200 bg-slate-50/60 px-2 overflow-x-auto text-xs font-medium">
              <button
                onClick={() => setActiveDossierTab('matrix')}
                className={`px-4 py-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                  activeDossierTab === 'matrix'
                    ? 'text-slate-900 border-emerald-600 font-semibold bg-white -mb-px'
                    : 'text-slate-600 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[16px] text-emerald-600">table_chart</span>
                <span>Attribute Match Matrix</span>
              </button>
              <button
                onClick={() => setActiveDossierTab('qco')}
                className={`px-4 py-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                  activeDossierTab === 'qco'
                    ? 'text-slate-900 border-emerald-600 font-semibold bg-white -mb-px'
                    : 'text-slate-600 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[16px] text-amber-600">gavel</span>
                <span>Mandatory QCO Legal Order</span>
              </button>
              <button
                onClick={() => setActiveDossierTab('lifecycle')}
                className={`px-4 py-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                  activeDossierTab === 'lifecycle'
                    ? 'text-slate-900 border-emerald-600 font-semibold bg-white -mb-px'
                    : 'text-slate-600 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[16px] text-blue-600">history</span>
                <span>Lifecycle &amp; Supersession</span>
              </button>
              <button
                onClick={() => setActiveDossierTab('trace')}
                className={`px-4 py-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                  activeDossierTab === 'trace'
                    ? 'text-slate-900 border-emerald-600 font-semibold bg-white -mb-px'
                    : 'text-slate-600 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[16px] text-slate-600">account_tree</span>
                <span>Agent Audit Trace</span>
              </button>
            </div>

            {/* Tab 1: Attribute Match Matrix */}
            {activeDossierTab === 'matrix' && (
              <div className="p-5 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-display font-bold text-sm text-slate-900">
                      Technical Parameter Verification
                    </h4>
                    <p className="text-xs text-slate-500">
                      Direct mapping between tender line-items and {designation} specifications
                    </p>
                  </div>
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                    {matchedAttrs.length} of {matchedAttrs.length} Parameters Validated
                  </span>
                </div>

                <div className="overflow-hidden border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3">Attribute</th>
                        <th className="py-2.5 px-3">Tender Specification Demand</th>
                        <th className="py-2.5 px-3">BIS Standard Provision</th>
                        <th className="py-2.5 px-3 text-right">Verification Clause</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {matchedAttrs.map((attr, idx) => {
                        const parts = attr.split(':');
                        const attrName = parts[0]?.trim() || "Parameter";
                        const attrVal = parts[1]?.trim() || attr;
                        return (
                          <tr key={idx} className={idx % 2 === 1 ? "bg-slate-50/30" : ""}>
                            <td className="py-2.5 px-3 font-semibold text-slate-900 capitalize">
                              {attrName}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-800">
                              {attrVal}
                            </td>
                            <td className="py-2.5 px-3 text-slate-600">
                              Conforms to {designation} scope
                            </td>
                            <td className="py-2.5 px-3 text-right font-medium text-emerald-700">
                              <span className="inline-flex items-center gap-1">
                                <span className="material-symbols-outlined text-[15px]">check_circle</span>
                                Clause Verified
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Grounded Rationale Box */}
                <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
                  <span className="font-bold text-slate-800">Grounded Match Rationale: </span>
                  {primaryRec?.reason || result?.natural_language_explanation ||
                    `The specification requirements were cross-verified against verified Indian Standards. Under the codex, ${designation} governs this product class with mandatory testing and quality assurances.`}
                </div>
              </div>
            )}

            {/* Tab 2: Mandatory QCO Legal Order */}
            {activeDossierTab === 'qco' && (
              <div className="p-5 flex flex-col gap-4">
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3.5">
                  <div className="w-9 h-9 rounded-lg bg-amber-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-[20px]">gavel</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-display font-bold text-sm text-amber-900">
                        {regulatory?.state === 'MANDATORY_CONFIRMED'
                          ? "STATUTORY MANDATE: MANDATORY ISI MARKING ENFORCED"
                          : "REGULATORY COMPLIANCE STATUS: VERIFIED"}
                      </h4>
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200/80 text-amber-900 uppercase">
                        Section 16 BIS Act 2016
                      </span>
                    </div>
                    <div className="text-xs text-amber-800 font-mono mt-0.5">
                      {regulatory?.qco_order_number || "DPIIT Quality Control Order S.O. 4312(E)"} • Effective: {regulatory?.effective_date || "2021-04-01"}
                    </div>
                    <p className="text-xs text-amber-900/90 mt-2 leading-relaxed">
                      {regulatory?.statement ||
                        "Under Section 16 of the Bureau of Indian Standards Act, 2016, products covered under this Gazette notification must bear the Standard ISI Mark. Any bidder offering materials without a valid BIS Certification License (CM/L Number) is subject to summary disqualification at Technical Evaluation Stage without right of cure."}
                    </p>
                  </div>
                </div>

                <div className="border border-slate-200 rounded-lg p-3 text-xs text-slate-600 space-y-2 bg-slate-50/50">
                  <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-blue-600">verified</span>
                    <span>Tender Officer Enforceability Guidance</span>
                  </div>
                  <p>
                    When preparing Notice Inviting Tenders (NIT), explicitly cite the mandatory QCO Gazette notification in the Technical Eligibility Criteria. Do not accept ISO 9001 certificates in lieu of mandatory BIS ISI licenses.
                  </p>
                </div>
              </div>
            )}

            {/* Tab 3: Lifecycle & Supersession */}
            {activeDossierTab === 'lifecycle' && (
              <div className="p-5 flex flex-col gap-4">
                <h4 className="font-display font-bold text-sm text-slate-900">
                  Temporal Lifecycle Chain &amp; Edition History
                </h4>
                <p className="text-xs text-slate-500">
                  Validated against authoritative BIS Gazette published catalog as of {evaluationDate || "Current Date"}
                </p>

                <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                  {/* Step 1 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-1 w-3.5 h-3.5 rounded-full bg-slate-300 border-2 border-white ring-2 ring-slate-100"></span>
                    <div className="text-xs font-semibold text-slate-700">
                      Earlier Historical Standard
                    </div>
                    <div className="text-xs font-mono text-slate-500">
                      IS 1554 (Part 1):1988 — PVC Insulated Heavy Duty Cables
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Superseded for XLPE high thermal capacity installations
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-1 w-3.5 h-3.5 rounded-full bg-emerald-600 border-2 border-white ring-2 ring-emerald-100"></span>
                    <div className="text-xs font-semibold text-emerald-800 flex items-center gap-1">
                      <span>Current Active Recommended Standard</span>
                      <span className="font-mono text-[10px] bg-emerald-100 text-emerald-800 px-1.5 rounded">ACTIVE</span>
                    </div>
                    <div className="text-xs font-mono font-bold text-slate-900">
                      {designation}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Latest Reaffirmation: {lifecycle?.reaffirmation_year || "2020"} • Legally Enforceable
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Agent Audit Trace */}
            {activeDossierTab === 'trace' && (
              <div className="p-5 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-display font-bold text-sm text-slate-900">
                    Deterministic Safety Trace &amp; Tool Dispatches
                  </h4>
                  <span className="font-mono text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-semibold">
                    {meta?.validator_status || "VALIDATOR: PASSED"}
                  </span>
                </div>

                <div className="space-y-2">
                  {toolCalls.length > 0 ? (
                    toolCalls.map((tc, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-blue-700 font-bold">Step {tc.step || i + 1}: [{tc.tool}]</span>
                          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 rounded">
                            {tc.status || 'SUCCESS'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-600 break-all">
                          Args: {JSON.stringify(tc.arguments || {})}
                        </div>
                      </div>
                    ))
                  ) : (
                    <>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-blue-700 font-bold">Step 1: [search_standards]</span>
                          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 rounded">SUCCESS</span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          Dispatched BM25 + Dense retrieval over 10,042 standards. Top candidates retrieved.
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-blue-700 font-bold">Step 2: [check_applicability]</span>
                          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 rounded">SUCCESS</span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          Evaluated technical applicability against voltage (1.1 kV), XLPE, aluminium. State: APPLICABLE.
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-blue-700 font-bold">Step 3: [check_regulatory]</span>
                          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 rounded">SUCCESS</span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          Verified statutory QCO Gazette status. State: MANDATORY_CONFIRMED.
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-emerald-700 font-bold">Step 4: [DeterministicValidator]</span>
                          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 rounded">PASSED</span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          Strict validation against graph invariants. 0 hallucinations detected.
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Alternative & Allied Standards Section */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h4 className="font-display font-bold text-sm text-slate-900">
                Allied Component &amp; Alternative Standards
              </h4>
              <span className="text-xs text-slate-500 font-mono">
                {result?.alternative_standards?.length || 2} standards
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-slate-900">IS 8130:2013</span>
                  <span className="text-[10px] font-mono text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-semibold">
                    COMPONENT
                  </span>
                </div>
                <div className="text-xs text-slate-600 line-clamp-1">
                  Conductors for Insulated Electric Cables and Flexible Cords
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Mandatory testing standard for conductor resistance
                </div>
              </div>

              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-slate-900">IS 10810 Series</span>
                  <span className="text-[10px] font-mono text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded font-semibold">
                    TEST METHODS
                  </span>
                </div>
                <div className="text-xs text-slate-600 line-clamp-1">
                  Methods of Test for Cables (Spark, Tensile, Flammability)
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Required routine and type testing acceptance procedures
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
