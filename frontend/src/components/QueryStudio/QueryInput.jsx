import React from 'react';
import ExampleQueries from './ExampleQueries';

export default function QueryInput({
  query,
  setQuery,
  mode,
  setMode,
  loading,
  onAnalyze,
  onClear,
}) {
  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setQuery(text);
    } catch (err) {
      console.warn("Clipboard access denied:", err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (query.trim() && !loading) {
        onAnalyze();
      }
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col gap-6">
      {/* Hero Question */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold font-display tracking-tight text-slate-900">
            What are you procuring?
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Enter your natural-language procurement requirement, tender clause, or technical parameters.
          </p>
        </div>

        {/* Input Mode Selector */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl border border-slate-200/80 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setMode('pipeline')}
            disabled={loading}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              mode === 'pipeline'
                ? 'bg-white text-emerald-800 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Fast Pipeline
          </button>
          <button
            type="button"
            onClick={() => setMode('auto')}
            disabled={loading}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              mode === 'auto'
                ? 'bg-white text-emerald-800 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Autonomous Agent</span>
          </button>
        </div>
      </div>

      {/* Main Textarea */}
      <div className="flex flex-col gap-2">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            rows={4}
            placeholder="e.g., Supply of 11 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground power cables conforming to standard specifications with outer extruded PVC sheathing..."
            className="w-full p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white focus:bg-white text-slate-900 placeholder:text-slate-400 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all resize-y shadow-inner font-sans"
          />

          {/* Quick Clear / Paste Controls inside Textarea footer */}
          <div className="flex items-center justify-between mt-1 px-1 text-xs text-slate-400">
            <div className="flex items-center gap-3">
              <span>{query.length} characters</span>
              <span className="hidden sm:inline">• Press Ctrl+Enter to submit</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={pasteFromClipboard}
                disabled={loading}
                className="hover:text-slate-700 flex items-center gap-1 text-[11px] font-medium transition-colors"
                title="Paste from clipboard"
              >
                <span className="material-symbols-outlined text-[14px]">content_paste</span>
                <span>Paste</span>
              </button>
              {query && (
                <button
                  type="button"
                  onClick={onClear}
                  disabled={loading}
                  className="hover:text-rose-600 flex items-center gap-1 text-[11px] font-medium transition-colors ml-2"
                  title="Clear input"
                >
                  <span className="material-symbols-outlined text-[14px]">clear</span>
                  <span>Clear</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Example Chips */}
      <ExampleQueries onSelectExample={(exampleText) => setQuery(exampleText)} disabled={loading} />

      {/* Action Row */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-slate-100">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="material-symbols-outlined text-[16px] text-emerald-600">verified</span>
          <span>Scope: Civil Engineering (CED) &amp; Electrotechnical (ETD) Standards</span>
        </div>

        <button
          type="button"
          onClick={onAnalyze}
          disabled={!query.trim() || loading}
          className="w-full sm:w-auto px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm transition-all shadow-sm hover:shadow flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-emerald-600"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
              <span>Analyzing Requirement...</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[18px]">search</span>
              <span>Analyze Procurement Requirement</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
