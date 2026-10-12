from typing import Dict, List, Optional, Any, Tuple
from app.schemas.response import EvidenceObject, EvidenceItem
from app.retrieval.hybrid_retriever import CandidateEvidence
from app.evidence_engine.ambiguity_detector import ambiguity_detector
from app.evidence_engine.refusal_handler import refusal_handler
from app.evidence_engine.evidence_checker import evidence_checker
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.policy_loader import policy_loader

class DecisionEngine:
    """
    Deterministic Evidence Engine.
    Evaluates retrieved candidates against strict truth requirements and outputs
    ANSWER, CLARIFY, or REFUSE with traceable evidence objects.
    """

    def evaluate(
        self,
        query: str,
        parsed_query: Dict[str, Any],
        product_candidates: List[CandidateEvidence],
        policy_candidate: Optional[CandidateEvidence]
    ) -> EvidenceObject:
        # 1. Conflicting Constraints Check
        has_conflict, conflict_msg = ambiguity_detector.detect_conflicting_constraints(parsed_query)
        if has_conflict:
            return EvidenceObject(
                decision="CLARIFY",
                query=query,
                evidence=[],
                unsupported_fields=[],
                clarification_question=f"I noticed contradictory criteria: {conflict_msg} Could you clarify your budget?",
                refusal_reason=None
            )

        # 2. Policy-focused Query Handling
        if parsed_query.get("is_policy_query") or (policy_candidate and not parsed_query.get("product_id") and not parsed_query.get("category")):
            if not policy_loader.is_ready or not policy_candidate:
                refusal = refusal_handler.create_unsupported_policy_refusal(
                    topic=parsed_query.get("policy_topic", "General"),
                    specific_query=query
                )
                return EvidenceObject(
                    decision="REFUSE",
                    query=query,
                    evidence=[],
                    unsupported_fields=["policy_terms"],
                    clarification_question=None,
                    refusal_reason=refusal["reason"]
                )

            # Check for negative / unsupported policy questions (e.g. international shipping)
            q_lower = query.lower()
            sec_data = policy_candidate.data
            sec_content = sec_data.get("content", "").lower()

            if any(term in q_lower for term in ["international", "canada", "usa", "worldwide", "uk"]):
                if "international" not in sec_content and "canada" not in sec_content:
                    return EvidenceObject(
                        decision="REFUSE",
                        query=query,
                        evidence=[],
                        unsupported_fields=["international_shipping"],
                        clarification_question=None,
                        refusal_reason="The policy document does not support international shipping outside India."
                    )

            # Verified policy answer
            sec_id = policy_candidate.source_id
            evidence_items = [
                evidence_checker.extract_policy_evidence(
                    section_id=sec_id,
                    field="content",
                    matched_text=sec_data.get("content", "")
                )
            ]
            return EvidenceObject(
                decision="ANSWER",
                query=query,
                evidence=evidence_items,
                unsupported_fields=[],
                clarification_question=None,
                refusal_reason=None
            )

        # 3. Product Catalogue Readiness Check
        if not catalogue_loader.is_ready:
            refusal = refusal_handler.create_empty_catalogue_refusal()
            return EvidenceObject(
                decision="REFUSE",
                query=query,
                evidence=[],
                unsupported_fields=["catalogue_data"],
                clarification_question=None,
                refusal_reason=refusal["reason"]
            )

        # 4. Exact Product ID Lookup Handling
        req_pid = parsed_query.get("product_id")
        if req_pid:
            prod = catalogue_loader.get_product(req_pid)
            if not prod:
                refusal = refusal_handler.create_out_of_catalogue_refusal(query, search_term=req_pid)
                return EvidenceObject(
                    decision="REFUSE",
                    query=query,
                    evidence=[],
                    unsupported_fields=[f"product_id:{req_pid}"],
                    clarification_question=None,
                    refusal_reason=refusal["reason"]
                )

            # Verify requested attributes exist on this product
            requested_attrs = parsed_query.get("requested_attributes", [])
            missing_attrs = []
            for attr in requested_attrs:
                if not structured_search_engine.has_attribute(prod, attr):
                    missing_attrs.append(attr)

            if missing_attrs:
                refusal = refusal_handler.create_unsupported_attribute_refusal(
                    product_title=prod["title"],
                    product_id=prod["product_id"],
                    missing_attribute=", ".join(missing_attrs)
                )
                return EvidenceObject(
                    decision="REFUSE",
                    query=query,
                    evidence=[],
                    unsupported_fields=missing_attrs,
                    clarification_question=None,
                    refusal_reason=refusal["reason"]
                )

            evidence_items = evidence_checker.extract_product_evidence(prod, requested_attrs)
            return EvidenceObject(
                decision="ANSWER",
                query=query,
                evidence=evidence_items,
                unsupported_fields=[],
                clarification_question=None,
                refusal_reason=None
            )

        # 5. General & Filtered Product Candidates Grounding Verification
        import re
        from app.retrieval.semantic_search import STOP_WORDS
        grounded_candidates = []
        query_words = [
            w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', query)
            if w.lower() not in STOP_WORDS and w.lower() not in ("product", "have", "looking", "item", "items")
        ]

        for cand in product_candidates:
            if cand.retrieval_method in ("structured", "hybrid"):
                grounded_candidates.append(cand)
            else:
                # Semantic-only candidate: ensure at least one significant query term is grounded in product text
                prod = cand.data
                prod_text = f"{prod.get('title', '')} {prod.get('category', '')} {prod.get('description', '')} {prod.get('attributes', {})}".lower()
                if not query_words:
                    grounded_candidates.append(cand)
                else:
                    matches = [w for w in query_words if w in prod_text]
                    if matches and (len(matches) / len(query_words) >= 0.4 or any(w in prod.get('title', '').lower() for w in matches)):
                        grounded_candidates.append(cand)

        product_candidates = grounded_candidates

        if not product_candidates:
            refusal = refusal_handler.create_out_of_catalogue_refusal(query)
            return EvidenceObject(
                decision="REFUSE",
                query=query,
                evidence=[],
                unsupported_fields=["matching_products"],
                clarification_question=None,
                refusal_reason=refusal["reason"]
            )

        raw_candidates = [c.data for c in product_candidates]

        # 6. Ambiguity Check
        is_ambiguous, clarification_q = ambiguity_detector.check_candidate_ambiguity(
            candidates=raw_candidates,
            parsed_query=parsed_query
        )
        if is_ambiguous:
            return EvidenceObject(
                decision="CLARIFY",
                query=query,
                evidence=[],
                unsupported_fields=[],
                clarification_question=clarification_q,
                refusal_reason=None
            )

        # 7. Unambiguous Approved Answer
        evidence_items = []
        for cand in product_candidates[:3]:
            items = evidence_checker.extract_product_evidence(
                product=cand.data,
                requested_fields=parsed_query.get("requested_attributes", [])
            )
            evidence_items.extend(items)

        return EvidenceObject(
            decision="ANSWER",
            query=query,
            evidence=evidence_items,
            unsupported_fields=[],
            clarification_question=None,
            refusal_reason=None
        )

# Import structured_search_engine for attribute verification helper
from app.retrieval.structured_search import structured_search_engine

decision_engine = DecisionEngine()
