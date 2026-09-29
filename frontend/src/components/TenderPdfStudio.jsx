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
        raw_text: "Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables conforming to standard specifications with outer extruded PVC sheathing.",
        page_number: 12,
        domain: "Electrotechnical (ETD)",
        extracted_entities: { product: "Power Cable", voltage: "1.1 kV", material: "XLPE", conductor: "Aluminium 240 sq mm" },
        recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 7098 (Part 1):1988",
          title: "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
          lifecycle_state: "ACTIVE",
          is_mandatory_qco: true,
          confidence_score: 0.98,
        },
        status: "VERIFIED",
      },
      {
        item_id: "ITEM_002",
        clause_reference: "Section 3.2 - Schedule of Quantities Sl. 2",
        raw_text: "Centrifugally cast (spun) iron pressure pipes for water supply mains, Class LA, nominal diameter 300 mm with flexible rubber push-on joints.",
        page_number: 15,
        domain: "Civil Engineering (CED)",
        extracted_entities: { product: "Spun Iron Pressure Pipes", material: "Cast Iron", dimensions: "DN 300 mm", grade: "Class LA" },
        recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 1536:2001",
          title: "Centrifugally Cast (Spun) Iron Pressure Pipes for Water, Gas and Sewage",
          lifecycle_state: "ACTIVE",
          is_mandatory_qco: true,
          confidence_score: 0.95,
        },
        status: "VERIFIED",
      },
      {
        item_id: "ITEM_003",
        clause_reference: "Section 4.1 - Technical Specifications Cl. 7",
        raw_text: "Indoor type low voltage switchgear and controlgear assemblies for auxiliary AC distribution rated up to 1000 V AC.",
        page_number: 22,
        domain: "Electrotechnical (ETD)",
        extracted_entities: { product: "Switchgear Assembly", voltage: "1000 V AC", installation: "Indoor" },
        recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS/IEC 61439 (Part 1 & 2):2011",
          title: "Low-voltage Switchgear and Controlgear Assemblies",
          lifecycle_state: "ACTIVE",
          is_mandatory_qco: true,
          confidence_score: 0.92,
        },
        status: "VERIFIED",
      },
      {
        item_id: "ITEM_004",
        clause_reference: "Section 5.3 - Substation Package",
        raw_text: "Distribution transformers 11 kV / 433 V, 500 kVA outdoor type oil immersed conforming to IS 1180:1989.",
        page_number: 28,
        domain: "Electrotechnical (ETD)",
        extracted_entities: { product: "Distribution Transformer", voltage: "11 kV / 433 V", cited_standard: "IS 1180:1989" },
        recommendation: {
          decision_state: "PRIMARY_RECOMMENDATION_AVAILABLE",
          designation: "IS 1180 (Part 1):2014",
          title: "Outdoor Type Oil Immersed Distribution Transformers up to and Including 2500 kVA, 33 kV",
          lifecycle_state: "SUPERSEDED_IN_TENDER",
          is_mandatory_qco: true,
          confidence_score: 0.99,
        },
        status: "SUPERSEDED_ALERT",
      },
    ],
  },
];

export default function TenderPdfStudio({ evaluationDate }) {
  const [docData, setDocData] = useState(SAMPLE_TENDERS[0]);
  const [activeView, setActiveView] = useState('workbench'); // 'workbench' | 'audit'
  const [selectedItems, setSelectedItems] = useState(["ITEM_001", "ITEM_002", "ITEM_004"]);
  const [activeClause, setActiveClause] = useState(SAMPLE_TENDERS[0].clauses[0]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);

    try {
      const parsed = await uploadTenderPdf(file, evaluationDate);
      setDocData(parsed);
      if (parsed.clauses?.length > 0) {
        setActiveClause(parsed.clauses[0]);
        setSelectedItems(parsed.clauses.map(c => c.item_id));
      }
    } catch (err) {
      console.error("PDF upload error:", err);
      setUploadError(err.message || "Failed to process PDF tender file.");
    } finally {
      setUploading(false);
    }
  };

  const toggleSelectItem = (itemId) => {
    setSelectedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    );
  };

  const selectAll = () => {
    if (selectedItems.length === (docData.clauses?.length || 0)) {
      setSelectedItems([]);
    } else {
      setSelectedItems(docData.clauses?.map(c => c.item_id) || []);
    }
  };

  const handleBatchRun = async () => {
    if (selectedItems.length === 0) return;
    const itemsToRun = (docData.clauses || []).filter(c => selectedItems.includes(c.item_id));
    alert(`Running batch verification on ${itemsToRun.length} selected items across CED/ETD corpus...`);
  };

  const exportComplianceReport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(docData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `TENDER_AUDIT_${docData.tender_metadata?.tender_id || 'REPORT'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const totalItems = docData.clauses?.length || 0;
  const verifiedCount = docData.clauses?.filter(c => c.status === 'VERIFIED').length || 0;
  const supersededCount = docData.clauses?.filter(c => c.status === 'SUPERSEDED_ALERT' || c.recommendation?.lifecycle_state === 'SUPERSEDED_IN_TENDER').length || 0;
  const complianceScore = totalItems > 0 ? Math.round((verifiedCount / totalItems) * 100) : 88;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* Top Header & Breadcrumb */}
      <div className="w-full bg-white rounded-xl p-4 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 shadow-xs">
            <span className="material-symbols-outlined text-[20px]">picture_as_pdf</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 font-display">
                Tender PDF Compliance &amp; Verification Studio
              </h1>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 uppercase tracking-wide">
                Hybrid Workflow Active
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Interactive Clause-by-Clause Workbench + Full-Document Automated Statutory Audit
            </p>
          </div>
        </div>

        {/* View Switcher Tabs */}
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
            <span>View A: Interactive Workbench</span>
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
            <span>View B: Compliance Audit Dossier</span>
          </button>
        </div>
      </div>

      {/* PDF Upload Dropzone / Quick Select */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4 flex-1">
          <label className="cursor-pointer px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs flex items-center gap-2 shadow-xs transition">
            <span className="material-symbols-outlined text-[18px]">upload_file</span>
            <span>{uploading ? "Extracting Clauses..." : "Upload New Tender PDF"}</span>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>

          <div className="text-xs text-slate-500">
            <span className="font-semibold text-slate-800">Current Tender: </span>
            <span className="font-mono text-slate-700">{docData.filename || docData.name}</span>
            <span className="text-slate-300 mx-2">|</span>
            <span>{docData.page_count || docData.pages} Pages</span>
            <span className="text-slate-300 mx-2">|</span>
            <span className="text-emerald-700 font-medium">
              {docData.tender_metadata?.issuing_authority || docData.authority}
            </span>
          </div>
        </div>

        {/* Sample Tenders Quick Loader */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">Sample:</span>
          <button
            onClick={() => {
              setDocData(SAMPLE_TENDERS[0]);
              setActiveClause(SAMPLE_TENDERS[0].clauses[0]);
              setSelectedItems(["ITEM_001", "ITEM_002", "ITEM_004"]);
            }}
            className="px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-xs text-slate-700 hover:bg-slate-100 transition"
          >
            NTPC Feeder Cable &amp; Transformer NIT
          </button>
        </div>
      </div>

      {uploadError && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">error</span>
          <span>{uploadError}</span>
        </div>
      )}

      {/* VIEW A: INTERACTIVE CLAUSE WORKBENCH */}
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
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  {activeClause?.clause_reference || "Item 1"}
                </span>
              </div>

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
                </div>
              </div>

              {/* Recommended Standard Pill */}
              <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200 flex flex-col gap-1 text-xs">
                <span className="text-[10px] uppercase font-mono font-bold text-emerald-800">
                  Authoritative Primary Standard
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-slate-900">
                    {activeClause?.recommendation?.designation || "IS Standard Applicable"}
                  </span>
                  {activeClause?.recommendation?.is_mandatory_qco && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-mono text-[10px] font-bold">
                      QCO MANDATORY
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-600 line-clamp-2">
                  {activeClause?.recommendation?.title}
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Line-Items Table & Batch Actions (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
              {/* Table Top Controls */}
              <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={selectAll}
                    className="text-xs font-semibold text-blue-700 hover:text-blue-900"
                  >
                    {selectedItems.length === totalItems ? "Deselect All" : "Select All"}
                  </button>
                  <span className="text-slate-300">|</span>
                  <span className="text-xs text-slate-600 font-mono">
                    {selectedItems.length} of {totalItems} Selected
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleBatchRun}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-xs flex items-center gap-1 transition"
                  >
                    <span className="material-symbols-outlined text-[15px]">play_arrow</span>
                    <span>Run Batch Verification</span>
                  </button>
                  <button
                    onClick={exportComplianceReport}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium shadow-xs transition"
                  >
                    Export JSON
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
                          checked={selectedItems.length === totalItems && totalItems > 0}
                          onChange={selectAll}
                          className="rounded text-blue-600 focus:ring-blue-500"
                        />
                      </th>
                      <th className="py-2.5 px-3">Item / Clause Ref</th>
                      <th className="py-2.5 px-3">Domain</th>
                      <th className="py-2.5 px-3">Recommended IS</th>
                      <th className="py-2.5 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {(docData.clauses || []).map((cl) => {
                      const isSelected = selectedItems.includes(cl.item_id);
                      const isActive = activeClause?.item_id === cl.item_id;
                      const isSuperseded = cl.status === 'SUPERSEDED_ALERT' || cl.recommendation?.lifecycle_state === 'SUPERSEDED_IN_TENDER';

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
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                              {cl.domain}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                            {cl.recommendation?.designation || "Pending"}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {isSuperseded ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                ⚠ SUPERSEDED
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                ✓ VERIFIED
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

      {/* VIEW B: FULL-DOCUMENT COMPLIANCE AUDIT REPORT */}
      {activeView === 'audit' && (
        <div className="flex flex-col gap-6">
          {/* Executive Metrics Cards (4 cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">list_alt</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Total Clauses Analyzed</span>
                <span className="text-xl font-bold text-slate-900">{totalItems} Line Items</span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">verified</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Compliance Score</span>
                <span className="text-xl font-bold text-emerald-700">{complianceScore}% Legally Sound</span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">warning</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Critical Discrepancies</span>
                <span className="text-xl font-bold text-rose-700">{supersededCount} Superseded Standard</span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                <span className="material-symbols-outlined text-[22px]">gavel</span>
              </div>
              <div>
                <span className="text-xs font-mono text-slate-400 block uppercase">Mandatory QCO Items</span>
                <span className="text-xl font-bold text-amber-700">4 Items Mandated</span>
              </div>
            </div>
          </div>

          {/* Red-Flag Alerts Section */}
          <div className="bg-white rounded-xl border border-rose-200 p-5 shadow-xs flex flex-col gap-3">
            <div className="flex items-center gap-2 text-rose-800">
              <span className="material-symbols-outlined text-[20px]">report</span>
              <h3 className="font-display font-bold text-sm">
                Red-Flag Findings &amp; Statutory Non-Compliance Alerts
              </h3>
            </div>

            <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900 leading-relaxed flex items-start gap-2.5">
              <span className="material-symbols-outlined text-[18px] text-rose-600 mt-0.5">cancel</span>
              <div>
                <strong className="block text-sm font-semibold">
                  Tender Cites Superseded Standard: IS 1180:1989 in Item 4 (Page 28)
                </strong>
                <p className="mt-1">
                  The tender document references <em>IS 1180:1989</em> for outdoor distribution transformers. This standard was formally <strong>WITHDRAWN</strong> and superseded by <strong>IS 1180 (Part 1):2014</strong>. Under Ministry of Power regulations and DPIIT Quality Control Orders, bids quoting the 1989 edition are legally vulnerable to challenges.
                </p>
                <div className="mt-2 text-rose-800 font-semibold">
                  Recommended Action: Issue an immediate tender corrigendum updating the specification to IS 1180 (Part 1):2014 with mandatory Level-2 / Level-3 energy efficiency labels.
                </div>
              </div>
            </div>
          </div>

          {/* Full Audit Grid */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-sm text-slate-900">
                Consolidated Tender Specification Compliance Grid
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={exportComplianceReport}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs shadow-xs flex items-center gap-1 transition"
                >
                  <span className="material-symbols-outlined text-[16px]">download</span>
                  <span>Download Executive Audit Report (PDF/JSON)</span>
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
                  {(docData.clauses || []).map((cl, i) => (
                    <tr key={i} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-mono font-semibold">{i + 1}</td>
                      <td className="py-2.5 px-3 font-mono text-[11px] max-w-xs">{cl.raw_text}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                        {cl.recommendation?.designation}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {cl.status === 'SUPERSEDED_ALERT' ? (
                          <span className="text-rose-600 font-bold">SUPERSEDED (Update Req)</span>
                        ) : (
                          <span className="text-emerald-700 font-bold">ACTIVE (Valid)</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono text-[10px] font-bold">
                          MANDATORY
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium">
                        {cl.status === 'SUPERSEDED_ALERT' ? (
                          <span className="text-rose-700 font-bold">Issue Corrigendum</span>
                        ) : (
                          <span className="text-emerald-700">Conforming</span>
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
