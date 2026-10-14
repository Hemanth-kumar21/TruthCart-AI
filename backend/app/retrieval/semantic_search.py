import os
import re
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
    "i", "please", "show", "tell", "give", "want", "need", "find", "looking", "available"
}

SYNONYMS: Dict[str, List[str]] = {
    "shoes": ["footwear", "shoe", "sneakers"],
    "shoe": ["footwear", "shoes", "sneakers"],
    "sneakers": ["shoes", "shoe", "footwear"],
    "sneaker": ["shoes", "shoe", "footwear"],
    "footwear": ["shoes", "shoe", "slippers", "sandals", "boots"],
    "slippers": ["flip flops", "slipper", "slides", "sandals", "chappals"],
    "slipper": ["slippers", "flip flops", "slides", "sandals"],
    "chappals": ["slippers", "flip flops", "sandals"],
    "chappal": ["slippers", "flip flops", "sandals"],
    "clothes": ["clothing", "apparel", "wear", "shirt", "shirts", "tops"],
    "clothing": ["clothes", "apparel", "wear"],
    "apparel": ["clothing", "clothes", "wear"],
    "tshirt": ["t-shirt", "tee", "top", "shirt"],
    "t-shirt": ["tshirt", "tee", "top", "shirt"],
    "shirts": ["shirt", "t-shirt", "apparel", "clothing"],
    "shirt": ["shirts", "clothing", "apparel"],
    "earbuds": ["earphones", "earbud", "headphones", "audio"],
    "earphones": ["earbuds", "earphone", "headphones", "audio"],
    "headphones": ["earphones", "headphone", "audio", "earbuds"],
    "smartwatch": ["watch", "smartwatches", "wearable"],
    "watch": ["smartwatch", "watches", "wearable"],
    "bag": ["courier bags", "bags", "packaging"],
    "bags": ["courier bags", "bag", "packaging"],
    "lamp": ["lighting", "lamps", "light", "study lamp"],
    "lamps": ["lighting", "lamp", "light", "study lamp"],
    "mats": ["mat", "yoga mat", "yoga"],
    "mat": ["mats", "yoga mat", "yoga"],
    "dumbbell": ["dumbbells", "weights", "fitness"],
    "dumbbells": ["dumbbell", "weights", "fitness"],
    "sets": ["set", "combo", "dumbbell sets", "bedsheet sets"],
    "set": ["sets", "combo"]
}

def stem_word(word: str) -> str:
    """Lightweight rule-based English normalizer for shopping vocabulary."""
    w = word.lower().strip()
    if len(w) <= 3:
        return w
    if w.endswith("oes"):
        return w[:-1] # shoes -> shoe
    if w.endswith("sses"):
        return w[:-2] # glasses -> glass
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y" # batteries -> battery
    if w.endswith("ches") or w.endswith("shes") or w.endswith("xes"):
        return w[:-2] # watches -> watch, dishes -> dish
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1] # running -> run
        return base
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1] # fitted -> fit
        return base
    if w.endswith("s") and not w.endswith("ss") and not w.endswith("us") and not w.endswith("is"):
        return w[:-1] # slippers -> slipper, mats -> mat
    return w

class LocalVectorIndex:
    """
    Lightweight, CPU-friendly vector index.
    Features robust shopping stemming, synonym expansion, weighted multi-field documents,
    and cosine similarity ranking.
    Fully offline, zero external API calls.
    """

    def __init__(self):
        self.doc_ids: List[str] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.is_indexed: bool = False
        self.cache_path: Path = settings.get_index_path() / "catalogue_vector_index.pkl"

    def _tokenize(self, text: str, expand_synonyms: bool = False) -> List[str]:
        cleaned = re.sub(r'[>>/\\_,\-\(\)\[\]:]', ' ', str(text).lower())
        raw_tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', cleaned)
        tokens: List[str] = []
        for t in raw_tokens:
            if t in STOP_WORDS:
                continue
            st = stem_word(t)
            tokens.append(t)
            if st != t:
                tokens.append(st)
            if expand_synonyms and t in SYNONYMS:
                for syn in SYNONYMS[t]:
                    for syn_w in syn.split():
                        if syn_w not in STOP_WORDS:
                            tokens.append(syn_w)
                            st_syn = stem_word(syn_w)
                            if st_syn != syn_w:
                                tokens.append(st_syn)
        return tokens

    def build_index(self, force_rebuild: bool = False) -> bool:
        """Builds vector index from currently loaded catalogue with multi-field weighting."""
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
                        SafeLogger.info(f"Loaded cached local vector index ({len(self.doc_ids)} items).")
                        return True
            except Exception as e:
                SafeLogger.warning(f"Could not load cached index: {str(e)}")

        self.doc_ids = []
        doc_tokens: List[List[str]] = []
        for p in products:
            self.doc_ids.append(p["product_id"])
            title = p.get("title", "")
            cat_clean = p.get("category", "").replace(">>", " ")
            desc = p.get("description", "")
            brand = p.get("brand", "")
            color = p.get("color", "")
            material = p.get("material", "")
            attrs = " ".join([f"{k} {v}" for k, v in p.get("attributes", {}).items()])
            # Emphasize title (3x) and category (2x) for high relevance ranking
            full_text = f"{title} {title} {title} {cat_clean} {cat_clean} {desc} {brand} {color} {material} {attrs}"
            tokens = self._tokenize(full_text, expand_synonyms=False)
            doc_tokens.append(tokens)

        # Build vocabulary and document frequencies
        df: Dict[str, int] = {}
        num_docs = len(doc_tokens)
        for tokens in doc_tokens:
            for term in set(tokens):
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
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for term, count in tf.items():
                if term in self.vocabulary:
                    term_idx = self.vocabulary[term]
                    matrix[doc_idx, term_idx] = (count / len(tokens)) * self.idf[term]

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

    def query(self, query_text: str, top_k: int = 50, min_score: float = 0.04) -> List[Tuple[Dict[str, Any], float]]:
        """Computes cosine similarity between query and catalogue items with synonym expansion."""
        if not self.is_indexed or self.tfidf_matrix is None or not self.doc_ids:
            self.build_index()
            if not self.is_indexed:
                return []

        tokens = self._tokenize(query_text, expand_synonyms=True)
        if not tokens:
            return []

        matched_tokens = [t for t in tokens if t in self.vocabulary]
        if not matched_tokens:
            return []

        query_vec = np.zeros(len(self.vocabulary), dtype=np.float32)
        tf: Dict[str, int] = {}
        for t in matched_tokens:
            tf[t] = tf.get(t, 0) + 1

        for term, count in tf.items():
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

        results: List[Tuple[Dict[str, Any], float]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= min_score:
                prod_id = self.doc_ids[idx]
                prod = catalogue_loader.get_product(prod_id)
                if prod:
                    results.append((prod, score))

        return results

    def search(self, query_text: str, top_k: int = 50, min_score: float = 0.04) -> List[Tuple[Dict[str, Any], float]]:
        """Alias for query."""
        return self.query(query_text=query_text, top_k=top_k, min_score=min_score)

local_vector_index = LocalVectorIndex()
