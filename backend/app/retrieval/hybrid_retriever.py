from typing import Dict, List, Optional, Any, Tuple
from app.retrieval.structured_search import structured_search_engine
from app.retrieval.semantic_search import local_vector_index
from app.retrieval.policy_search import policy_search_engine, PolicySection
from app.core.logging_config import SafeLogger

class CandidateEvidence:
    """Encapsulates a retrieved candidate record with scoring and provenance metadata."""
    def __init__(
        self,
        source_type: str, # "product" or "policy"
        source_id: str,
        data: Dict[str, Any],
        retrieval_method: str, # "structured", "semantic", "hybrid", "policy"
        score: float = 1.0
    ):
        self.source_type = source_type
        self.source_id = source_id
        self.data = data
        self.retrieval_method = retrieval_method
        self.score = score

class HybridRetriever:
    """
    Combines structured filtering, semantic vector similarity, and policy retrieval.
    Guarantees that candidates maintain traceable link to source records.
    """

    def retrieve(
        self,
        query: str,
        structured_params: Dict[str, Any],
        top_k: int = 5
    ) -> Tuple[List[CandidateEvidence], Optional[CandidateEvidence]]:
        """
        Executes hybrid retrieval.
        Returns:
            product_candidates: List of candidate products.
            policy_candidate: Matching policy section if query pertains to policy, else None.
        """
        product_candidates: List[CandidateEvidence] = []
        policy_candidate: Optional[CandidateEvidence] = None

        # 1. Policy Retrieval Check
        policy_matches = policy_search_engine.search(query)
        if policy_matches:
            top_sec, p_score = policy_matches[0]
            policy_candidate = CandidateEvidence(
                source_type="policy",
                source_id=top_sec.section_id,
                data=top_sec.to_dict(),
                retrieval_method="policy",
                score=p_score
            )

        # 2. Structured Product Search
        has_structured_filters = any(
            v is not None for k, v in structured_params.items()
            if k in ("product_id", "max_price", "min_price", "category", "brand", "color", "material", "stock_required", "min_rating")
        )
        
        structured_results = []
        if has_structured_filters:
            structured_results = structured_search_engine.search(**structured_params)
            for p in structured_results:
                product_candidates.append(
                    CandidateEvidence(
                        source_type="product",
                        source_id=p["product_id"],
                        data=p,
                        retrieval_method="structured",
                        score=1.0
                    )
                )

        # 3. Semantic Search (as complementary signal)
        semantic_results = local_vector_index.query(query, top_k=top_k)
        
        # Merge semantic and structured candidates
        seen_ids = {c.source_id for c in product_candidates}
        for p, s_score in semantic_results:
            pid = p["product_id"]
            if pid not in seen_ids:
                # If structured filters are present, verify that candidate satisfies filters
                if has_structured_filters:
                    # Only add if it didn't violate strict price/stock constraints
                    if structured_params.get("max_price") and p.get("price", 0) > structured_params["max_price"]:
                        continue
                    if structured_params.get("stock_required") and p.get("stock_status", "").lower() not in ("in stock", "available"):
                        continue
                product_candidates.append(
                    CandidateEvidence(
                        source_type="product",
                        source_id=pid,
                        data=p,
                        retrieval_method="semantic",
                        score=s_score
                    )
                )
                seen_ids.add(pid)
            else:
                # Update candidate to hybrid with higher combined confidence
                for c in product_candidates:
                    if c.source_id == pid:
                        c.retrieval_method = "hybrid"
                        c.score = min(1.0, c.score + (s_score * 0.2))

        # Sort by candidate score
        product_candidates.sort(key=lambda x: x.score, reverse=True)
        return product_candidates[:top_k], policy_candidate

hybrid_retriever = HybridRetriever()
