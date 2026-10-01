import React, { useState } from 'react';
import QueryInput from './QueryStudio/QueryInput';
import EmptyState from './QueryStudio/EmptyState';
import AnalysisProgress from './QueryStudio/AnalysisProgress';
import DecisionSummary from './QueryStudio/DecisionSummary';
import RecommendationCard from './QueryStudio/RecommendationCard';
import AbstentionCard from './QueryStudio/AbstentionCard';
import EvidenceSummary from './QueryStudio/EvidenceSummary';
import AlternativeStandards from './QueryStudio/AlternativeStandards';
import ProgressiveEvidenceTabs from './QueryStudio/ProgressiveEvidenceTabs';

export default function QueryStudio({ evaluationDate }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('pipeline'); // 'pipeline' | 'auto'
  const [loading, setLoading] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [error, setError] = useState(null);

  const handleClear = () => {
    setQuery('');
    setQueryResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/query/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          mode: mode,
          evaluation_date: evaluationDate || null,
          top_k: 5,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned error status ${response.status}`);
      }

      const data = await response.json();
      setQueryResult(data);
    } catch (err) {
      console.error("Analysis request failed:", err);
      setError(err.message || "Failed to analyze procurement requirement. Ensure the API server is active.");
    } finally {
      setLoading(false);
    }
  };

  // Inspect results
  const decisionState = queryResult?.decision_state;
  const primaryRec = queryResult?.primary_recommendation;
  const isReviewCandidate = decisionState === 'EXPERT_REVIEW_REQUIRED';
  const displayStandard = primaryRec || (isReviewCandidate && queryResult?.candidate_for_review);
  const candidates = queryResult?.candidate_recommendations || queryResult?.candidates || [];
  const alliedStandards = queryResult?.allied_standards || [];
  const rejectedCandidates = queryResult?.rejected_candidates || [];
  const abstentionReason = queryResult?.abstention_reason || queryResult?.caveat;

  const isAbstained = [
    'INSUFFICIENT_INFORMATION',
    'CLARIFICATION_REQUIRED',
    'NO_CONFIDENT_MATCH',
    'OUTSIDE_PROTOTYPE_COVERAGE',
    'SUPERSEDED_STANDARD_IN_QUERY',
    'AMBIGUOUS_QUERY_VOLTAGE_OR_MATERIAL_ABSENT',
  ].includes(decisionState);

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col gap-6">
      {/* 1. Procurement Query Input Area */}
      <QueryInput
        query={query}
        setQuery={setQuery}
        mode={mode}
        setMode={setMode}
        loading={loading}
        onAnalyze={handleAnalyze}
        onClear={handleClear}
      />

      {/* 2. Error Banner */}
      {error && (
        <div className="w-full p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3">
          <span className="material-symbols-outlined text-[20px] text-rose-600 shrink-0">error</span>
          <div className="flex-1 text-xs">
            <strong className="block font-bold">Analysis Request Error:</strong>
            <p className="mt-0.5 text-rose-800">{error}</p>
          </div>
          <button
            type="button"
            onClick={handleAnalyze}
            className="px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {/* 3. Loading State */}
      {loading && <AnalysisProgress mode={mode} />}

      {/* 4. Empty State (before first search) */}
      {!loading && !queryResult && !error && (
        <EmptyState onSelectExample={(exampleText) => setQuery(exampleText)} />
      )}

      {/* 5. Analysis Results View */}
      {!loading && queryResult && (
        <div className="flex flex-col gap-6 animate-fadeIn">
          {/* Decision Verdict Banner */}
          <DecisionSummary
            decisionState={decisionState}
            abstentionReason={abstentionReason}
            claimLevel={queryResult?.claim_level}
            language={queryResult?.query?.language || queryResult?.normalized_requirements?.language_detection?.detected}
          />

          {/* If Abstained or Needs Clarification */}
          {isAbstained && (
            <AbstentionCard
              decisionState={decisionState}
              abstentionReason={abstentionReason}
              query={query}
              queryResult={queryResult}
            />
          )}

          {/* Primary Recommendation or Candidate for Review */}
          {displayStandard && (
            <>
              <RecommendationCard
                standard={displayStandard}
                isReviewCandidate={isReviewCandidate}
                decisionState={decisionState}
                abstentionReason={abstentionReason}
              />

              {/* 6-point Evidence Summary Strip */}
              <EvidenceSummary standard={displayStandard} />

              {/* Detailed Progressive Tabs */}
              <ProgressiveEvidenceTabs
                standard={displayStandard}
                queryResult={queryResult}
              />
            </>
          )}

          {/* Alternative Candidates & Allied Standards */}
          <AlternativeStandards
            candidates={candidates}
            alliedStandards={alliedStandards}
            rejectedCandidates={rejectedCandidates}
          />
        </div>
      )}
    </div>
  );
}
