import os
import math
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from app.core.config import settings
from app.core.logging_config import SafeLogger
from app.ingestion.catalogue_loader import catalogue_loader

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "it", "its", "do", "does", "did", "you",
    "your", "we", "our", "me", "my", "have", "has", "had", "can", "could", "would",
    "should", "what", "which", "who", "whom", "this", "that", "these", "those",
    "i", "please", "show", "tell", "give", "want", "need", "find"
}

class LocalVectorIndex:
    """
    Lightweight, CPU-friendly vector index.
    Supports local dense embedding adapter or fast BM25/TF-IDF vector space with cosine similarity.
    Fully offline, zero external API calls.
    """

    def __init__(self):
        self.doc_ids: List[str] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.is_indexed: bool = False
        self.cache_path: Path = settings.get_index_path() / "catalogue_vector_index.pkl"

    def _tokenize(self, text: str) -> List[str]:
        import re
        tokens = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', text)]
        return [t for t in tokens if t not in STOP_WORDS]

    def build_index(self, force_rebuild: bool = False) -> bool:
        """Builds vector index from currently loaded catalogue."""
        products = catalogue_loader.get_all_products()
        if not products:
            self.is_indexed = False
            return False

        # Try to load cached index if valid and matching
        if not force_rebuild and self.cache_path.exists():
            try:
                with open(self.cache_path, "rb") as f:
                    cached = pickle.load(f)
                    if cached.get("doc_ids") == [p["product_id"] for p in products]:
                        self.doc_ids = cached["doc_ids"]
                        self.vocabulary = cached["vocabulary"]
                        self.idf = cached["idf"]
                        self.tfidf_matrix = cached["tfidf_matrix"]
                        self.is_indexed = True
                        SafeLogger.info("Loaded cached local vector index from disk.")
                        return True
            except Exception as e:
                SafeLogger.warning(f"Could not load cached index: {str(e)}")

        self.doc_ids = []
        doc_tokens = []
        for p in products:
            self.doc_ids.append(p["product_id"])
            attrs_str = " ".join([f"{k} {v}" for k, v in p.get("attributes", {}).items()])
            text = f"{p.get('title', '')} {p.get('category', '')} {p.get('description', '')} {attrs_str}"
            tokens = self._tokenize(text)
            doc_tokens.append(tokens)

        # Build vocabulary and document frequencies
        df = {}
        num_docs = len(doc_tokens)
        for tokens in doc_tokens:
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1

        self.vocabulary = {term: idx for idx, term in enumerate(sorted(df.keys()))}
        self.idf = {
            term: math.log((num_docs + 1) / (count + 1)) + 1.0
            for term, count in df.items()
        }

        # Build TF-IDF matrix
        vocab_size = len(self.vocabulary)
        matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)

        for doc_idx, tokens in enumerate(doc_tokens):
            if not tokens:
                continue
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for term, count in tf.items():
                if term in self.vocabulary:
                    term_idx = self.vocabulary[term]
                    matrix[doc_idx, term_idx] = (count / len(tokens)) * self.idf[term]

            # Normalize row
            norm = np.linalg.norm(matrix[doc_idx])
            if norm > 0:
                matrix[doc_idx] /= norm

        self.tfidf_matrix = matrix
        self.is_indexed = True

        # Cache locally
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "wb") as f:
                pickle.dump({
                    "doc_ids": self.doc_ids,
                    "vocabulary": self.vocabulary,
                    "idf": self.idf,
                    "tfidf_matrix": self.tfidf_matrix
                }, f)
            SafeLogger.info(f"Built and cached local vector index for {num_docs} products.")
        except Exception as e:
            SafeLogger.warning(f"Could not persist index cache: {str(e)}")

        return True

    def query(self, query_text: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Computes cosine similarity between query and catalogue items."""
        if not self.is_indexed or self.tfidf_matrix is None or not self.doc_ids:
            self.build_index()
            if not self.is_indexed:
                return []

        tokens = self._tokenize(query_text)
        if not tokens:
            return []

        query_vec = np.zeros(len(self.vocabulary), dtype=np.float32)
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        for term, count in tf.items():
            if term in self.vocabulary:
                idx = self.vocabulary[term]
                query_vec[idx] = (count / len(tokens)) * self.idf[term]

        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec /= norm
        else:
            return []

        # Cosine similarity
        scores = np.dot(self.tfidf_matrix, query_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= 0.20: # Calibrated minimum relevance threshold
                prod_id = self.doc_ids[idx]
                prod = catalogue_loader.get_product(prod_id)
                if prod:
                    results.append((prod, score))

        return results

local_vector_index = LocalVectorIndex()
