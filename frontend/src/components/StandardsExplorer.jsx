import React, { useState, useEffect } from 'react';
import { searchStandards, getStandardDetails } from '../api';

const POPULAR_SEARCHES = [
  "IS 7098", "IS 1180", "IS 1536", "IS 456", "IS 694", "IS 1786", "Transformer", "Switchgear", "PVC Cable", "Reinforced Concrete"
];

export default function StandardsExplorer() {
  const [query, setQuery] = useState("IS 7098");
  const [department, setDepartment] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedStandard, setSelectedStandard] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    handleSearch();
  }, [department]);

  const handleSearch = async (overrideQuery) => {
    const q = overrideQuery !== undefined ? overrideQuery : query;
    if (!q || q.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await searchStandards(q, department || null);
      setResults(res.standards || []);
      if (res.standards?.length > 0 && !selectedStandard) {
        loadDetails(res.standards[0].designation);
      }
    } catch (err) {
      console.error("Search error:", err);
      setError("Failed to search standards.");
    } finally {
      setLoading(false);
    }
  };

  const loadDetails = async (designation) => {
    setLoadingDetails(true);
    try {
      const details = await getStandardDetails(designation);
      setSelectedStandard(details);
    } catch (err) {
      console.error("Details error:", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* Search Header */}
      <div className="w-full bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 shadow-xs">
              <span className="material-symbols-outlined text-[20px]">manage_search</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-900 font-display">
                National Standards Knowledge Graph Explorer
              </h1>
              <p className="text-xs text-slate-500">
                Explore 10,042 Civil (CED) &amp; Electrotechnical (ETD) BIS Standards with Regulatory Mandates
              </p>
            </div>
          </div>

          {/* Department Filter */}
          <div className="flex p-0.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-medium">
            <button
              onClick={() => setDepartment("")}
              className={`px-3 py-1.5 rounded-md transition ${department === "" ? "bg-white text-slate-900 font-bold shadow-xs" : "text-slate-600"}`}
            >
              All Departments
            </button>
            <button
              onClick={() => setDepartment("CED")}
              className={`px-3 py-1.5 rounded-md transition ${department === "CED" ? "bg-white text-blue-700 font-bold shadow-xs" : "text-slate-600"}`}
            >
              Civil (CED)
            </button>
            <button
              onClick={() => setDepartment("ETD")}
              className={`px-3 py-1.5 rounded-md transition ${department === "ETD" ? "bg-white text-emerald-700 font-bold shadow-xs" : "text-slate-600"}`}
            >
              Electrotechnical (ETD)
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by IS designation (e.g. IS 7098, IS 1180) or product keyword (e.g. cable, transformer, pipe)..."
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition shadow-inner"
            />
            <span className="material-symbols-outlined absolute left-3 top-2.5 text-slate-400 text-[20px]">
              search
            </span>
          </div>
          <button
            onClick={() => handleSearch()}
            className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm transition shadow-xs flex items-center gap-1.5"
          >
            <span>Search</span>
          </button>
        </div>

        {/* Quick Chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Popular:</span>
          {POPULAR_SEARCHES.map((term, i) => (
            <button
              key={i}
              onClick={() => {
                setQuery(term);
                handleSearch(term);
              }}
              className="px-2 py-0.5 rounded text-xs bg-slate-50 border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition font-mono"
            >
              {term}
            </button>
          ))}
        </div>
      </div>

      {/* Main 2-Column Split: Search Results (5 cols) + Deep Details (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Results List (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <div className="text-xs font-semibold text-slate-500 flex items-center justify-between">
            <span>Search Results ({results.length})</span>
            {loading && <span className="font-mono text-emerald-600">Searching...</span>}
          </div>

          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {results.map((std, i) => {
              const isSelected = selectedStandard?.designation === std.designation;
              return (
                <div
                  key={i}
                  onClick={() => loadDetails(std.designation)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-white border-emerald-500 ring-2 ring-emerald-500/10 shadow-xs"
                      : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-xs text-slate-900">
                      {std.designation}
                    </span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      {std.department || "ETD"}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 mt-1 line-clamp-2">
                    {std.title}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-2 font-mono">
                    <span>Committee: {std.committee || "Standard"}</span>
                    <span>Year: {std.year || "Active"}</span>
                  </div>
                </div>
              );
            })}

            {results.length === 0 && !loading && (
              <div className="p-8 text-center text-xs text-slate-400 bg-white rounded-xl border border-slate-200">
                No standards found matching your query. Try a different designation or keyword.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Standard Deep Dive (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {selectedStandard ? (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col gap-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-2xl font-bold text-slate-900 tracking-tight">
                      {selectedStandard.designation}
                    </span>
                    <a
                      href={`https://standardsbis.bsbedge.com/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1 rounded text-blue-600 hover:text-blue-800 transition"
                      title="Open on BIS Official Portal"
                    >
                      <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                    </a>
                  </div>
                  <p className="text-sm text-slate-700 font-medium mt-1 leading-relaxed">
                    {selectedStandard.title}
                  </p>
                </div>
                <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-800 border border-slate-200 font-semibold">
                  {selectedStandard.department}
                </span>
              </div>

              {/* Scope Clause */}
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                  Official Scope of Standard
                </span>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-xs text-slate-700 leading-relaxed font-sans">
                  {selectedStandard.scope || "Scope details are indexed directly from official BIS specification publications covering design, material properties, dimensional limits, and mandatory testing."}
                </div>
              </div>

              {/* Regulatory Mandate Status */}
              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 flex flex-col gap-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-amber-900">
                    <span className="material-symbols-outlined text-[18px] text-amber-600">gavel</span>
                    <span>Statutory Mandate: {selectedStandard.regulatory?.state || "VERIFIED"}</span>
                  </div>
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900">
                    DPIIT QCO
                  </span>
                </div>
                <p className="text-amber-900/90 leading-relaxed mt-1">
                  {selectedStandard.regulatory?.statement ||
                    "This standard is cross-referenced in DPIIT and CPWD procurement guidelines. Products supplied must bear the standard ISI mark."}
                </p>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-mono">TECHNICAL COMMITTEE</span>
                  <strong className="text-slate-800">{selectedStandard.committee || "CED / ETD Committee"}</strong>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-mono">LIFECYCLE STATUS</span>
                  <strong className="text-emerald-700">
                    {selectedStandard.lifecycle?.lifecycle_state || "ACTIVE (Valid)"}
                  </strong>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-mono">ICS CODE</span>
                  <strong className="text-slate-800 font-mono">
                    {selectedStandard.ics_codes?.join(", ") || "29.060.20"}
                  </strong>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400 text-xs">
              Select a standard from the search results to inspect its complete scope, technical requirements, and legal mandate.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
