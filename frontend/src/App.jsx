import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import QueryStudio from './components/QueryStudio';
import TenderPdfStudio from './components/TenderPdfStudio';
import StandardsExplorer from './components/StandardsExplorer';
import AuditLogs from './components/AuditLogs';
import { fetchHealth } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('query'); // 'query' | 'tender' | 'standards' | 'audit'
  const [health, setHealth] = useState(null);
  const [evaluationDate, setEvaluationDate] = useState('2026-09-30');

  useEffect(() => {
    fetchHealth().then(setHealth).catch(console.error);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased selection:bg-emerald-100 selection:text-emerald-800">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        evaluationDate={evaluationDate}
        setEvaluationDate={setEvaluationDate}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {activeTab === 'query' && <QueryStudio evaluationDate={evaluationDate} />}
        {activeTab === 'tender' && <TenderPdfStudio evaluationDate={evaluationDate} />}
        {activeTab === 'standards' && <StandardsExplorer />}
        {activeTab === 'audit' && <AuditLogs health={health} />}
      </main>

      {/* Footer */}
      <footer className="w-full bg-white border-t border-slate-200 py-4 px-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">StandSpec AI Platform</span>
            <span>•</span>
            <span>National Standard Regulatory Corroboration Engine</span>
            <span>•</span>
            <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 border border-slate-200">
              Release: {health?.release_id || 'v3.0.0'}
            </span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <span>Bureau of Indian Standards Act 2016</span>
            <span>•</span>
            <span>DPIIT / CPWD Schedule Compliant</span>
            <span>•</span>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
              Zero-Hallucination Guard Active
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
