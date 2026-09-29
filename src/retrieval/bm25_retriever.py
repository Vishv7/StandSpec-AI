"""
BM25 Lexical Retrieval Baseline — StandSpec AI (Layer 1 Indexing & Baseline 1)
Implements domain-aware weighted field BM25 (Okapi BM25) over standards designations,
titles, scopes, and committee/ICS metadata.
Preserves Indian standard designations, engineering units, material grades,
and multilingual Indic Unicode tokens.
Zero heavy dependencies, highly performant, deterministic.
"""

import math
import re
from collections import Counter
from pathlib import Path


# English stop words list (domain-neutral, excluding 'is' to protect BIS designations)
STOP_WORDS = frozenset([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "per", "shall", "standard", "prescribes", "requirements"
])

INDIC_WORD_PATTERN = re.compile(
    r'[a-zA-Z0-9_\u0900-\u097F\u0A80-\u0AFF\u0B80-\u0BFF\u0C00-\u0C7F\u0980-\u09FF]+'
)


def tokenize(text: str) -> list[str]:
    """
    Domain-aware tokenizer for Indian Standards and procurement texts:
    1. Extracts and canonicalizes standard designations (e.g. 'IS 7098 (Part 2):2011' -> 'is_7098', 'is_7098_part_2').
    2. Normalizes technical engineering units & material grades (e.g. '11 kV' -> '11kv', 'Fe 500D' -> 'fe_500d').
    3. Preserves Unicode words for Indian languages (Devanagari, Gujarati, Tamil, etc.).
    4. Filters English stop words without corrupting standard prefixes.
    """
    if not text:
        return []

    tokens = []

    # 1. Extract and canonicalize standard designations
    # Captures: IS 1786, IS/IEC 60947-2:2016, IS 7098 (Part 2):2011, IEC 61439-1
    std_pattern = re.compile(
        r'\b(IS(?:\s*/\s*IEC)?|IEC|BS|EN)\s*(\d+[a-zA-Z]?(?:-\d+)?)(?:\s*\(([^)]+)\))?(?::\d{4})?',
        re.IGNORECASE
    )

    def replace_std(match):
        prefix = match.group(1)
        num = match.group(2)
        part = match.group(3)

        prefix_clean = re.sub(r'[\s/\-]+', '_', prefix.lower())
        num_clean = re.sub(r'[\s/\-]+', '_', num.lower())
        base_clean = f"{prefix_clean}_{num_clean}"
        tokens.append(base_clean)

        # Base number
        pure_num = re.search(r'\d+', num)
        if pure_num:
            tokens.append(pure_num.group(0))

        # Sub-part / section
        if part:
            part_clean = re.sub(r'[\s/\-]+', '_', part.lower())
            tokens.append(f"{base_clean}_{part_clean}")
            tokens.append(part_clean)
        return " "

    processed_text = std_pattern.sub(replace_std, text)

    # 2. Extract technical units, voltages, frequencies, parts, and steel/cement grades
    unit_patterns = [
        (r'\bpart\s*(\d+)\b', r'part_\1'),
        (r'\bsec(?:tion)?\s*(\d+)\b', r'sec_\1'),
        (r'\b(\d+)\s*k[vV]\b', r'\1kv'),
        (r'\b(\d+)\s*[vV]\b', r'\1v'),
        (r'\b(\d+)\s*[mM][vV][aA]\b', r'\1mva'),
        (r'\b(\d+)\s*[kK][vV][aA]\b', r'\1kva'),
        (r'\b(\d+)\s*[kK][wW]\b', r'\1kw'),
        (r'\b(\d+)\s*[hH][zZ]\b', r'\1hz'),
        (r'\b(\d+)\s*[mM][pP][aA]\b', r'\1mpa'),
        (r'\b(\d+)\s*(?:sq\.?\s*mm|sqmm|mm2)\b', r'\1sqmm'),
        (r'\b(\d+)\s*mm\b', r'\1mm'),
        (r'\b([fF][eE])\s*[-]?\s*(\d+[a-zA-Z]?)\b', r'fe_\2'),
        (r'\b(\d+)\s*[gG]rade\b', r'\1_grade'),
        (r'\b[gG]rade\s*(\d+)\b', r'\1_grade'),
        (r'\b[dD][nN]\s*(\d+)\b', r'dn_\1'),
    ]
    for pat, repl in unit_patterns:
        for match in re.finditer(pat, processed_text, re.IGNORECASE):
            tok = re.sub(pat, repl, match.group(0), flags=re.IGNORECASE).lower()
            tokens.append(tok)
            # For Fe grades, also emit compact form
            if tok.startswith("fe_"):
                tokens.append(tok.replace("fe_", "fe"))
        processed_text = re.sub(pat, " ", processed_text, flags=re.IGNORECASE)

    # 3. Regular Unicode word tokenization (preserves Hindi, Gujarati, Devanagari, English)
    raw_words = INDIC_WORD_PATTERN.findall(processed_text.lower())
    for w in raw_words:
        if len(w) > 1 and w not in STOP_WORDS:
            tokens.append(w)
            # Suffix/plural normalization for English engineering nouns
            if w.isalpha():
                if any(w.endswith(sfx) for sfx in ['shes', 'ches', 'sses', 'xes', 'zes']) and len(w) > 4:
                    base = w[:-2]
                    if base not in STOP_WORDS:
                        tokens.append(base)
                elif w.endswith('s') and len(w) > 3 and w not in {'glass', 'class', 'brass', 'mass', 'pass', 'cross', 'loss', 'gas'}:
                    base = w[:-1]
                    if base not in STOP_WORDS:
                        tokens.append(base)

    return tokens


class BM25Retriever:
    """
    Weighted Field Okapi BM25 Indexer and Retriever.
    Supports title weighting, scope weighting, designation weighting, and metadata boosting.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        id_weight: float = 4.0,
        title_weight: float = 3.0,
        scope_weight: float = 1.0,
        meta_weight: float = 1.5,
    ):
        self.k1 = k1
        self.b = b
        self.id_weight = id_weight
        self.title_weight = title_weight
        self.scope_weight = scope_weight
        self.meta_weight = meta_weight

        self.documents = []  # List of raw doc dicts
        self.doc_ids = []    # List of standard designations
        self.doc_lengths = []
        self.avg_doc_len = 0.0

        self.term_doc_freq = Counter()  # Number of docs containing term
        self.term_freqs = []            # List of Counter(term: weighted_frequency) per doc
        self.idf = {}

    def index_documents(self, documents: list[dict]):
        """
        Index a collection of standard document dicts.
        Each doc must have: 'designation' (or 'id'), and optionally 'title', 'scope', 'committee', 'ics_codes'.
        """
        self.documents = documents
        self.doc_ids = [d.get("designation") or d.get("id") for d in documents]
        n_docs = len(documents)

        self.term_doc_freq.clear()
        self.term_freqs = []
        self.doc_lengths = []

        total_length = 0

        for doc in documents:
            desig_tokens = tokenize(doc.get("designation") or doc.get("id", "") or "")
            title_tokens = tokenize(doc.get("title", "") or "")
            scope_tokens = tokenize(doc.get("scope", "") or "")
            meta_tokens = tokenize(f"{doc.get('committee', '')} {' '.join(doc.get('ics_codes', []) or [])}")

            doc_tf = Counter()
            for t in desig_tokens:
                doc_tf[t] += self.id_weight
            for t in title_tokens:
                doc_tf[t] += self.title_weight
            for t in scope_tokens:
                doc_tf[t] += self.scope_weight
            for t in meta_tokens:
                doc_tf[t] += self.meta_weight

            self.term_freqs.append(doc_tf)

            # Document effective length
            doc_len = (
                len(desig_tokens) * self.id_weight
                + len(title_tokens) * self.title_weight
                + len(scope_tokens) * self.scope_weight
                + len(meta_tokens) * self.meta_weight
            )
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            # Update document frequencies
            unique_terms = set(doc_tf.keys())
            for t in unique_terms:
                self.term_doc_freq[t] += 1

        self.avg_doc_len = total_length / n_docs if n_docs > 0 else 0.0

        # Precompute Robertson-Spärck Jones IDF
        self.idf = {}
        for term, df in self.term_doc_freq.items():
            # Standard smoothed BM25 IDF
            idf_val = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            self.idf[term] = max(0.01, idf_val)

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Score all indexed documents against the query string.
        Returns top_k ranked documents with scores and matched keywords.
        """
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents:
            return []

        scores = [0.0] * len(self.documents)
        matched_terms_per_doc = [[] for _ in range(len(self.documents))]

        for q in query_tokens:
            if q not in self.idf:
                continue

            idf_q = self.idf[q]

            for doc_idx, doc_tf in enumerate(self.term_freqs):
                tf = doc_tf.get(q, 0.0)
                if tf > 0:
                    doc_len = self.doc_lengths[doc_idx]
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score_q = idf_q * ((tf * (self.k1 + 1.0)) / denominator)
                    scores[doc_idx] += score_q
                    matched_terms_per_doc[doc_idx].append(q)

        # Rank documents
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        for rank, idx in enumerate(ranked_indices[:top_k], 1):
            if scores[idx] <= 0.0:
                break
            doc = self.documents[idx]
            results.append({
                "rank": rank,
                "score": round(scores[idx], 4),
                "designation": self.doc_ids[idx],
                "title": doc.get("title"),
                "matched_terms": list(set(matched_terms_per_doc[idx])),
                "document": doc,
            })

        return results
