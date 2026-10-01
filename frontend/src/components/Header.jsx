import React from 'react';

export default function Header({
  activeTab,
  setActiveTab,
  health,
  evaluationDate,
  setEvaluationDate,
}) {
  return (
    <header className="sticky top-0 w-full z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="h-16 w-full max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left: Branding & Scope */}
        <div className="flex items-center gap-6">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setActiveTab('query')}
            role="button"
            tabIndex={0}
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-xs">
              <span className="material-symbols-outlined text-[22px]">verified_user</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-lg tracking-tight text-slate-900">
                  StandSpec<span className="text-emerald-600">.AI</span>
                </span>
                <span className="font-mono text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  Prototype Scope: CED + ETD
                </span>
              </div>
              <span className="text-xs text-slate-500 hidden sm:block">
                National Standard Recommendation Assistant
              </span>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-200 hidden lg:block"></div>

          {/* Navigation Tabs */}
          <nav className="hidden lg:flex items-center gap-1">
            <button
              onClick={() => setActiveTab('query')}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                activeTab === 'query'
                  ? 'font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs'
                  : 'font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Query Studio
            </button>
            <button
              onClick={() => setActiveTab('tender')}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                activeTab === 'tender'
                  ? 'font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs'
                  : 'font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Tender PDF
            </button>
            <button
              onClick={() => setActiveTab('standards')}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                activeTab === 'standards'
                  ? 'font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs'
                  : 'font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Standards Explorer
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                activeTab === 'audit'
                  ? 'font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs'
                  : 'font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Audit &amp; Verification
            </button>
          </nav>
        </div>

        {/* Right: Operational Status & Settings */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Status Pill: Reflects truthful connection state */}
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${
            health?.status === "READY"
              ? "bg-emerald-50/60 border-emerald-200 text-emerald-800"
              : (health?.status === "OFFLINE"
                  ? "bg-amber-50 border-amber-200 text-amber-800"
                  : "bg-slate-50 border-slate-200 text-slate-700")
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              health?.status === "READY" ? "bg-emerald-600" : (health?.status === "OFFLINE" ? "bg-amber-500" : "bg-slate-400 animate-pulse")
            }`}></span>
            <span className="font-medium">
              {health?.status === "READY" ? "System Ready" : (health?.status === "OFFLINE" ? "Backend Offline" : "Connecting...")}
            </span>
          </div>

          {/* As Of Date Pill */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-slate-200 text-xs font-medium text-slate-700 shadow-xs">
            <span className="material-symbols-outlined text-[16px] text-slate-500">calendar_today</span>
            <span className="hidden sm:inline text-slate-500">As-Of:</span>
            <input
              type="date"
              value={evaluationDate}
              onChange={(e) => setEvaluationDate(e.target.value)}
              className="bg-transparent border-0 p-0 text-xs font-semibold text-slate-900 focus:outline-none focus:ring-0 cursor-pointer"
              title="Evaluation as-of date for historical standards and amendments"
            />
          </div>
        </div>
      </div>

      {/* Mobile Navigation Bar */}
      <div className="lg:hidden flex items-center justify-around border-t border-slate-200 bg-slate-50 px-2 py-1 text-xs">
        <button
          onClick={() => setActiveTab('query')}
          className={`px-2.5 py-1.5 rounded font-medium ${
            activeTab === 'query' ? 'text-emerald-700 font-semibold bg-emerald-50' : 'text-slate-600'
          }`}
        >
          Query Studio
        </button>
        <button
          onClick={() => setActiveTab('tender')}
          className={`px-2.5 py-1.5 rounded font-medium ${
            activeTab === 'tender' ? 'text-emerald-700 font-semibold bg-emerald-50' : 'text-slate-600'
          }`}
        >
          Tender PDF
        </button>
        <button
          onClick={() => setActiveTab('standards')}
          className={`px-2.5 py-1.5 rounded font-medium ${
            activeTab === 'standards' ? 'text-emerald-700 font-semibold bg-emerald-50' : 'text-slate-600'
          }`}
        >
          Standards
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-2.5 py-1.5 rounded font-medium ${
            activeTab === 'audit' ? 'text-emerald-700 font-semibold bg-emerald-50' : 'text-slate-600'
          }`}
        >
          Audit
        </button>
      </div>
    </header>
  );
}
