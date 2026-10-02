"""
StandSpec AI Retrieval Subsystem.
Exports BM25 retriever, dense retriever, RRF candidate fusion,
cycle-safe graph expansion, cross-encoder reranker,
and Phase 7-8 retrieval diagnostics.
"""

from src.retrieval.bm25_retriever import BM25Retriever, tokenize
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.fusion import reciprocal_rank_fusion, FusionAgreement
from src.retrieval.graph_expansion import GraphCandidateExpander
from src.retrieval.cross_encoder import CrossEncoderReranker
from src.retrieval.retrieval_diagnostics import (
    RetrievalDiagnostics,
    RetrievalFailureMode,
    ChannelAgreement,
    enrich_error_taxonomy_with_retrieval,
)

__all__ = [
    "BM25Retriever",
    "tokenize",
    "DenseRetriever",
    "reciprocal_rank_fusion",
    "FusionAgreement",
    "GraphCandidateExpander",
    "CrossEncoderReranker",
    "RetrievalDiagnostics",
    "RetrievalFailureMode",
    "ChannelAgreement",
    "enrich_error_taxonomy_with_retrieval",
]

