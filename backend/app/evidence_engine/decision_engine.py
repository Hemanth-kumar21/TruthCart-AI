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
        # 0. Prompt Injection / Safety Guardrail Check
        if parsed_query.get("is_prompt_injection"):
            refusal = refusal_handler.create_prompt_injection_refusal()
            return EvidenceObject(
                decision="REFUSE",
                query=query,
                evidence=[],
                unsupported_fields=["security_policy"],
                clarification_question=None,
                refusal_reason=refusal["reason"]
            )

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

        # 2. Product Comparison Handling
        if parsed_query.get("intent") == "comparison":
            compare_pids = parsed_query.get("compare_product_ids", [])
            if len(compare_pids) >= 2:
                compared_prods = []
                missing_pids = []
                for c_pid in compare_pids:
                    p = catalogue_loader.get_product(c_pid)
                    if not p:
                        missing_pids.append(c_pid)
                    else:
                        compared_prods.append(p)

                if missing_pids:
                    refusal = refusal_handler.create_out_of_catalogue_refusal(query, search_term=", ".join(missing_pids))
                    return EvidenceObject(
                        decision="REFUSE",
                        query=query,
                        evidence=[],
                        unsupported_fields=missing_pids,
                        clarification_question=None,
                        refusal_reason=refusal["reason"]
                    )

                # Both products verified! Extract evidence for each product independently
                evidence_items = []
                for p in compared_prods:
                    items = evidence_checker.extract_product_evidence(p, parsed_query.get("requested_attributes", []))
                    evidence_items.extend(items)

                return EvidenceObject(
                    decision="ANSWER",
                    query=query,
                    evidence=evidence_items,
                    unsupported_fields=[],
                    clarification_question=None,
                    refusal_reason=None
                )

        # 2. Policy-focused Query Handling
        is_explicit_policy = (
            parsed_query.get("is_policy_query")
            or (
                policy_candidate is not None
                and not parsed_query.get("product_id")
                and not parsed_query.get("category")
                and parsed_query.get("max_price") is None
                and parsed_query.get("min_price") is None
                and parsed_query.get("policy_topic") is not None
            )
        )
        if is_explicit_policy:
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

            if any(term in q_lower for term in ["international", "australia", "canada", "usa", "worldwide", "uk", "overseas", "abroad"]):
                return EvidenceObject(
                    decision="REFUSE",
                    query=query,
                    evidence=[],
                    unsupported_fields=["international_shipping"],
                    clarification_question=None,
                    refusal_reason="International delivery outside India is strictly not supported by store policy."
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

        GENERIC_MODIFIERS = {"pro", "max", "mini", "lite", "plus", "ultra", "deal", "discount", "free", "sale", "new", "best", "top", "good", "brand"}
        non_generic_query = [w for w in query_words if w not in GENERIC_MODIFIERS]

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
                    non_generic_matches = [w for w in matches if w not in GENERIC_MODIFIERS]
                    if non_generic_query and not non_generic_matches:
                        continue
                    if matches and (len(matches) / len(query_words) >= 0.4 or any(w in prod.get('title', '').lower() for w in matches)):
                        grounded_candidates.append(cand)

        product_candidates = grounded_candidates

        if not product_candidates:
            req_subtype = parsed_query.get("requested_subtype")
            req_category = parsed_query.get("category")
            max_p = parsed_query.get("max_price")

            # Case A: Specific subtype requested (e.g. slippers) that does not exist, but broader category has products
            if req_subtype and req_category:
                cat_lower = req_category.lower()
                category_prods = [
                    p for p in catalogue_loader.get_all_products()
                    if cat_lower in p.get("category", "").lower() and p.get("stock_status", "").lower() in ("in stock", "available")
                ]
                if category_prods:
                    evidence_items = []
                    for p in category_prods[:3]:
                        evidence_items.extend(evidence_checker.extract_product_evidence(p, []))
                    return EvidenceObject(
                        decision="ANSWER",
                        query=query,
                        evidence=evidence_items,
                        unsupported_fields=[f"subtype:{req_subtype}"],
                        clarification_question=None,
                        refusal_reason=None
                    )

            # Case B: Budget constraint on a known category where no items fit the budget (e.g. Footwear under 2000)
            if req_category and max_p is not None:
                cat_lower = req_category.lower()
                category_prods = [
                    p for p in catalogue_loader.get_all_products()
                    if cat_lower in p.get("category", "").lower()
                ]
                if category_prods:
                    min_cat_price = min(p.get("price", 999999) for p in category_prods)
                    cheapest_prod = min(category_prods, key=lambda p: p.get("price", 999999))
                    refusal_msg = (
                        f"There are no {req_category} products under ₹{max_p:,.0f} in our official catalogue. "
                        f"Our lowest priced {req_category.lower()} item is {cheapest_prod['title']} at ₹{min_cat_price:,.0f} [PRODUCT:{cheapest_prod['product_id']}]."
                    )
                    evidence_items = evidence_checker.extract_product_evidence(cheapest_prod, ["price"])
                    return EvidenceObject(
                        decision="REFUSE",
                        query=query,
                        evidence=evidence_items,
                        unsupported_fields=[f"price_under_{max_p}"],
                        clarification_question=None,
                        refusal_reason=refusal_msg
                    )

            # Case C: Category with zero products in catalogue
            if req_category:
                cat_lower = req_category.lower()
                category_prods = [
                    p for p in catalogue_loader.get_all_products()
                    if cat_lower in p.get("category", "").lower()
                ]
                if not category_prods:
                    return EvidenceObject(
                        decision="REFUSE",
                        query=query,
                        evidence=[],
                        unsupported_fields=[f"category:{req_category}"],
                        clarification_question=None,
                        refusal_reason=f"No products found in the '{req_category}' category in our official catalogue."
                    )

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

        unsupported_fields = []
        req_subtype = parsed_query.get("requested_subtype")
        if req_subtype:
            matches_sub = any(
                req_subtype.lower() in f"{c.data.get('title', '')} {c.data.get('description', '')}".lower()
                for c in product_candidates
            )
            if not matches_sub:
                unsupported_fields.append(f"subtype:{req_subtype}")

        return EvidenceObject(
            decision="ANSWER",
            query=query,
            evidence=evidence_items,
            unsupported_fields=unsupported_fields,
            clarification_question=None,
            refusal_reason=None
        )


# Import structured_search_engine for attribute verification helper
from app.retrieval.structured_search import structured_search_engine

decision_engine = DecisionEngine()
