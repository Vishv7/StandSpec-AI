"""
Candidate Rerankers and Factory — StandSpec AI (Layer 3 Candidate Reranking)
Provides three explicitly named reranking modes and a factory:
1. RuleBasedReranker: Handcrafted domain-feature baseline using 12 modular features and ScoringPolicy.
2. NeuralCrossEncoderReranker: Pretrained neural cross-encoder with transparent hermetic fallback.
3. NoneReranker: Pass-through reranker without scoring changes.
4. create_reranker: Factory constructing the appropriate reranker mode.
"""

from typing import List, Dict, Any, Optional, Tuple

from src.retrieval.reranker_features import (
    BaseFeatureExtractor,
    DesignationAlignment,
    PartSectionAlignment,
    RoleAlignment,
    ProductCategoryAlignment,
    MaterialAlignment,
    ApplicationAlignment,
    TechnologyModifierAlignment,
    TechnicalParametersAlignment,
    ScopeBoundary,
    Specificity,
    CandidateEvidenceAvailability,
    ProcurementIntentAlignment,
    ContradictionPenalty,
    ScoringPolicy,
)


class BaseReranker:
    """Base interface for StandSpec candidate rerankers."""

    reranker_type: str = "base"
    model_name: Optional[str] = None
    model_loaded: bool = False
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    effective_mode: str = "base"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "reranker_type": self.reranker_type,
            "model_name": self.model_name,
            "model_loaded": self.model_loaded,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "effective_mode": self.effective_mode,
        }

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        req_obj: Optional[Dict[str, Any]] = None,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class NoneReranker(BaseReranker):
    """Pass-through reranker that preserves candidate order without scoring changes."""

    reranker_type: str = "none"
    model_name: Optional[str] = None
    model_loaded: bool = True
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    effective_mode: str = "none"

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        req_obj: Optional[Dict[str, Any]] = None,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        results = []
        meta = self.get_metadata()
        for rank, c in enumerate(candidates[:top_k], 1):
            item = dict(c)
            item["rank"] = rank
            item["rerank_score"] = float(item.get("score", 1.0 / rank))
            item["reranker_metadata"] = meta
            results.append(item)
        return results


class RuleBasedReranker(BaseReranker):
    """
    Rule-Based Feature Reranker Baseline.
    Scores (query, standard) pairs using 12 modular feature extractors
    and an explainable ScoringPolicy.
    """

    reranker_type: str = "rule_based"
    model_name: Optional[str] = None
    model_loaded: bool = True
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    effective_mode: str = "rule_based"

    def __init__(
        self,
        extractors: Optional[List[BaseFeatureExtractor]] = None,
        scoring_policy: Optional[ScoringPolicy] = None,
    ):
        self.extractors = extractors or [
            DesignationAlignment(),
            PartSectionAlignment(),
            RoleAlignment(),
            ProductCategoryAlignment(),
            MaterialAlignment(),
            ApplicationAlignment(),
            TechnologyModifierAlignment(),
            TechnicalParametersAlignment(),
            ScopeBoundary(),
            Specificity(),
            CandidateEvidenceAvailability(),
            ProcurementIntentAlignment(),
            ContradictionPenalty(),
        ]
        self.policy = scoring_policy or ScoringPolicy()

    def score_pair(
        self, query_text: str, candidate: dict, req_obj: dict = None
    ) -> Tuple[float, dict]:
        feature_results = []
        for ext in self.extractors:
            fr = ext.evaluate(query_text, candidate, req_obj=req_obj)
            feature_results.append(fr)

        prob_score, signals, diagnostics = self.policy.score(feature_results, candidate)
        candidate["rerank_diagnostics"] = diagnostics
        return prob_score, signals

    def why_ranked_above(self, cand_a: dict, cand_b: dict) -> str:
        return self.policy.why_ranked_above(cand_a, cand_b)

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        req_obj: Dict[str, Any] = None,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        from src.recommendation.role_classifier import RoleClassifier

        meta = self.get_metadata()
        scored_candidates = []
        for c in candidates:
            score, signals = self.score_pair(query_text, c, req_obj=req_obj)
            item = dict(c)
            item["rerank_score"] = score
            item["rerank_signals"] = signals
            item["reranker_metadata"] = meta
            item["standard_role"] = RoleClassifier.classify(c).value
            scored_candidates.append(item)

        scored_candidates.sort(
            key=lambda x: (
                -x["rerank_score"],
                -sum(x.get("rerank_signals", {}).values()),
                0 if x.get("is_hydrated", True) else 1,
                0 if x.get("candidate_status") != "SUPPORTING_ONLY" else 1,
                x.get("designation", ""),
            )
        )

        for rank, item in enumerate(scored_candidates[:top_k], 1):
            item["rank"] = rank

        return scored_candidates[:top_k]


class NeuralCrossEncoderReranker(BaseReranker):
    """
    Model-backed Neural Cross-Encoder Reranker.
    Uses pretrained CrossEncoder (e.g. cross-encoder/ms-marco-MiniLM-L-6-v2) for token cross-attention.
    Transparently reports fallback when neural weights are unavailable.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.reranker_type = "neural"
        self.model_name = model_name
        self._ce_model = None
        self._fallback_reranker = RuleBasedReranker()

        try:
            import importlib
            st_module = importlib.import_module("sentence_transformers")
            CrossEncoder = getattr(st_module, "CrossEncoder")
            self._ce_model = CrossEncoder(model_name)
            self.model_loaded = True
            self.fallback_used = False
            self.fallback_reason = None
            self.effective_mode = "NEURAL_CROSS_ENCODER"
        except Exception as e:
            self._ce_model = None
            self.model_loaded = False
            self.fallback_used = True
            self.fallback_reason = f"Neural cross-encoder load failed: {str(e)}"
            self.effective_mode = "RULE_BASED_FALLBACK"

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        req_obj: Dict[str, Any] = None,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        meta = self.get_metadata()

        if self.model_loaded and self._ce_model is not None:
            pairs = []
            for c in candidates:
                doc = c.get("document", c)
                text_b = f"{c.get('designation', '')} - {c.get('title', '')}. {doc.get('scope', '') or ''}"
                pairs.append([query_text, text_b])
            scores = self._ce_model.predict(pairs)
            reranked = []
            for i, c in enumerate(candidates):
                item = dict(c)
                item["rerank_score"] = round(float(scores[i]), 4)
                item["reranker_metadata"] = meta
                reranked.append(item)
            reranked.sort(key=lambda x: -x["rerank_score"])
            for rank, item in enumerate(reranked[:top_k], 1):
                item["rank"] = rank
            return reranked[:top_k]

        # Explicit fallback execution
        results = self._fallback_reranker.rerank(
            query_text, candidates, req_obj=req_obj, top_k=top_k
        )
        for r in results:
            r["reranker_metadata"] = meta
        return results


def create_reranker(mode: str = "rule_based", model_name: Optional[str] = None, **kwargs) -> BaseReranker:
    """
    Factory creating a candidate reranker adhering to the requested mode.
    Modes:
      - 'rule_based': RuleBasedReranker using 12 modular features.
      - 'neural': NeuralCrossEncoderReranker (with transparent fallback reporting).
      - 'none': NoneReranker pass-through.
    """
    mode_clean = (mode or "rule_based").lower().strip()
    if mode_clean in ("rule_based", "rules"):
        return RuleBasedReranker(**kwargs)
    elif mode_clean in ("neural", "cross_encoder"):
        m_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        return NeuralCrossEncoderReranker(model_name=m_name)
    elif mode_clean in ("none", "disabled", "passthrough"):
        return NoneReranker()
    else:
        # Default fail-safe
        return RuleBasedReranker(**kwargs)


class CrossEncoderReranker:
    """
    Unified Candidate Reranker Interface for backward compatibility.
    """

    def __init__(self, model_name: str = None, mode: str = None):
        if mode:
            self._impl = create_reranker(mode=mode, model_name=model_name)
        elif model_name:
            self._impl = create_reranker(mode="neural", model_name=model_name)
        else:
            self._impl = create_reranker(mode="rule_based")

    @property
    def reranker_type(self) -> str:
        return self._impl.reranker_type

    @property
    def model_loaded(self) -> bool:
        return self._impl.model_loaded

    @property
    def fallback_used(self) -> bool:
        return self._impl.fallback_used

    @property
    def effective_mode(self) -> str:
        return self._impl.effective_mode

    def get_metadata(self) -> Dict[str, Any]:
        return self._impl.get_metadata()

    def score_pair(self, query_text: str, candidate: dict, req_obj: dict = None) -> Tuple[float, dict]:
        if hasattr(self._impl, "score_pair"):
            return self._impl.score_pair(query_text, candidate, req_obj=req_obj)
        return 0.5, {}

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        req_obj: Dict[str, Any] = None,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        return self._impl.rerank(query_text, candidates, req_obj=req_obj, top_k=top_k)
