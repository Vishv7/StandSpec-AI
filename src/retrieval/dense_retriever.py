"""
Dense Semantic Retrievers — StandSpec AI (Layer 1 Dense Retrieval)
Provides two explicitly named retrieval modes and a factory:
1. DeterministicSemanticProjection: Zero-dependency, offline, deterministic 384-dim subword projection.
2. MultilingualDenseRetriever: Model-backed neural dense retriever (sentence-transformers / BGE) with transparent fallback reporting.
3. DenseRetriever: Unified factory / interface ensuring backward compatibility.
4. create_dense_retriever: Explicit factory function.
"""

import math
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


class DeterministicSemanticProjection:
    """
    Deterministic Semantic Feature Projection Baseline.
    Computes a 384-dimensional normalized vector via sublinear TF token hashing,
    character n-gram subword decomposition, and bigram features.
    Provides a reproducible, zero-network baseline.
    """

    retriever_type: str = "dense_deterministic"
    model_name: str = "deterministic_subword_projection_384d"
    model_loaded: bool = True
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    effective_mode: str = "DETERMINISTIC_DENSE_FALLBACK"
    index_version: str = "v2.1"

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.embedding_dimension = embedding_dim
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self.doc_embeddings: Optional[np.ndarray] = None

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "retriever_type": self.retriever_type,
            "model_name": self.model_name,
            "model_loaded": self.model_loaded,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "effective_mode": self.effective_mode,
            "embedding_dimension": self.embedding_dim,
            "index_version": self.index_version,
        }

    def _hash_token(self, token: str) -> Tuple[int, float]:
        h = 2166136261
        for char in token:
            h = (h ^ ord(char)) * 16777619
            h &= 0xFFFFFFFF
        idx = h % self.embedding_dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        return idx, sign

    def encode_text(self, text: str) -> np.ndarray:
        if not text:
            vec = np.zeros(self.embedding_dim, dtype=np.float32)
            vec[0] = 1.0
            return vec

        tokens = re.findall(r'[\w]+', text.lower())
        if not tokens:
            vec = np.zeros(self.embedding_dim, dtype=np.float32)
            vec[0] = 1.0
            return vec

        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        for i, t in enumerate(tokens):
            idx, sign = self._hash_token(t)
            vec[idx] += sign * (1.0 + math.log(1.0 + len(t)))
            if len(t) >= 4:
                for n in (3, 4):
                    for j in range(len(t) - n + 1):
                        ngram = t[j:j+n]
                        ng_idx, ng_sign = self._hash_token(ngram)
                        vec[ng_idx] += ng_sign * 0.5
            if i + 1 < len(tokens):
                bigram = f"{t}_{tokens[i+1]}"
                b_idx, b_sign = self._hash_token(bigram)
                vec[b_idx] += b_sign * 1.5

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        else:
            vec[0] = 1.0
        return vec

    def index_documents(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.doc_ids = [d.get("designation") or d.get("id") for d in documents]
        n_docs = len(documents)

        if n_docs == 0:
            self.doc_embeddings = np.zeros((0, self.embedding_dim), dtype=np.float32)
            return

        embeddings = []
        for doc in documents:
            text_chunks = [
                doc.get("designation") or doc.get("id", ""),
                doc.get("title", "") or "",
                doc.get("scope", "") or "",
                doc.get("committee", "") or "",
                " ".join(doc.get("ics_codes", []) or []),
            ]
            full_text = " ".join(c for c in text_chunks if c).strip()
            emb = self.encode_text(full_text)
            embeddings.append(emb)

        self.doc_embeddings = np.array(embeddings, dtype=np.float32)

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if self.doc_embeddings is None or len(self.documents) == 0:
            return []

        q_vec = self.encode_text(query)
        scores = np.dot(self.doc_embeddings, q_vec)

        actual_k = min(top_k, len(self.documents))
        if actual_k <= 0:
            return []

        meta = self.get_metadata()
        top_indices = np.argsort(scores)[::-1][:actual_k]
        results = []
        for rank, idx in enumerate(top_indices, start=1):
            doc = self.documents[idx]
            results.append({
                "designation": self.doc_ids[idx],
                "score": float(scores[idx]),
                "dense_score": float(scores[idx]),
                "rank": rank,
                "document": doc,
                "title": doc.get("title"),
                "retriever_metadata": meta,
            })
        return results


class MultilingualDenseRetriever:
    """
    Model-backed Multilingual Dense Retriever.
    Supports neural multilingual transformer models (e.g. BAAI/bge-m3 or sentence-transformers).
    Transparently reports fallback when neural weights are unavailable.
    """

    retriever_type: str = "dense_neural"
    index_version: str = "v2.1"

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        batch_size: int = 32,
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self.embedding_dimension = 384
        self._st_model = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self.doc_embeddings: Optional[np.ndarray] = None
        self._fallback_retriever = DeterministicSemanticProjection()

        try:
            import importlib
            st_module = importlib.import_module("sentence_transformers")
            SentenceTransformer = getattr(st_module, "SentenceTransformer")
            self._st_model = SentenceTransformer(model_name, device=device)
            self.model_loaded = True
            self.fallback_used = False
            self.fallback_reason = None
            self.effective_mode = "NEURAL_MULTILINGUAL_DENSE"
        except Exception as e:
            self._st_model = None
            self.model_loaded = False
            self.fallback_used = True
            self.fallback_reason = f"Neural embedding model load failed: {str(e)}"
            self.effective_mode = "DETERMINISTIC_DENSE_FALLBACK"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "retriever_type": self.retriever_type,
            "model_name": self.model_name,
            "model_loaded": self.model_loaded,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "effective_mode": self.effective_mode,
            "embedding_dimension": self.embedding_dimension,
            "index_version": self.index_version,
        }

    def encode_text(self, text: str) -> np.ndarray:
        if self.model_loaded and self._st_model is not None:
            emb = self._st_model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return emb.astype(np.float32)
        return self._fallback_retriever.encode_text(text)

    def index_documents(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.doc_ids = [d.get("designation") or d.get("id") for d in documents]
        n_docs = len(documents)

        if n_docs == 0:
            self.doc_embeddings = np.zeros((0, self.embedding_dimension), dtype=np.float32)
            return

        texts = []
        for doc in documents:
            text_chunks = [
                doc.get("designation") or doc.get("id", ""),
                doc.get("title", "") or "",
                doc.get("scope", "") or "",
                doc.get("committee", "") or "",
            ]
            texts.append(" ".join(c for c in text_chunks if c).strip())

        if self.model_loaded and self._st_model is not None:
            self.doc_embeddings = self._st_model.encode(
                texts, batch_size=self.batch_size, convert_to_numpy=True, normalize_embeddings=True
            ).astype(np.float32)
        else:
            self._fallback_retriever.index_documents(documents)
            self.doc_embeddings = self._fallback_retriever.doc_embeddings

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if self.doc_embeddings is None or len(self.documents) == 0:
            return []

        q_vec = self.encode_text(query)
        scores = np.dot(self.doc_embeddings, q_vec)

        actual_k = min(top_k, len(self.documents))
        if actual_k <= 0:
            return []

        meta = self.get_metadata()
        top_indices = np.argsort(scores)[::-1][:actual_k]
        results = []
        for rank, idx in enumerate(top_indices, start=1):
            doc = self.documents[idx]
            results.append({
                "designation": self.doc_ids[idx],
                "score": float(scores[idx]),
                "dense_score": float(scores[idx]),
                "rank": rank,
                "document": doc,
                "title": doc.get("title"),
                "retriever_metadata": meta,
            })
        return results


def create_dense_retriever(
    mode: str = "deterministic",
    model_name: Optional[str] = None,
    embedding_dim: int = 384,
    **kwargs
):
    """
    Factory creating a dense retriever adhering to the requested mode.
    Modes:
      - 'deterministic': DeterministicSemanticProjection (384-dim subword hashing)
      - 'neural': MultilingualDenseRetriever (with transparent fallback reporting)
    """
    mode_clean = (mode or "deterministic").lower().strip()
    if mode_clean in ("neural", "dense_neural"):
        m_name = model_name or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        return MultilingualDenseRetriever(model_name=m_name, **kwargs)
    else:
        return DeterministicSemanticProjection(embedding_dim=embedding_dim)


class DenseRetriever:
    """
    Unified Dense Retriever Interface for backward compatibility.
    """

    def __init__(self, embedding_dim: int = 384, model_name: str = None, mode: str = None):
        self.embedding_dim = embedding_dim
        self.model_name = model_name

        if mode:
            self._impl = create_dense_retriever(mode=mode, model_name=model_name, embedding_dim=embedding_dim)
        elif model_name:
            self._impl = create_dense_retriever(mode="neural", model_name=model_name, embedding_dim=embedding_dim)
        else:
            self._impl = create_dense_retriever(mode="deterministic", embedding_dim=embedding_dim)

    @property
    def retriever_type(self) -> str:
        return self._impl.retriever_type

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

    def encode_text(self, text: str) -> np.ndarray:
        return self._impl.encode_text(text)

    def index_documents(self, documents: List[Dict[str, Any]]):
        self._impl.index_documents(documents)

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        return self._impl.retrieve(query, top_k=top_k)

    @property
    def documents(self):
        return self._impl.documents

    @property
    def doc_embeddings(self):
        return self._impl.doc_embeddings
