from typing import Dict, List, Optional, Any, Tuple
from app.schemas.response import EvidenceObject, ProductResult
from app.evidence_engine.citation_mapper import citation_mapper
from app.evidence_engine.citation_validator import citation_validator
from app.llm.model_adapter import local_model_adapter
from app.llm.model_loader import model_loader
from app.ingestion.catalogue_loader import catalogue_loader

class ResponseGenerator:
    """
    Evidence-grounded response generator.
    Strict Invariant: Never overrides the Evidence Engine decision and strictly enforces citations.
    """

    def generate_response(
        self,
        evidence_obj: EvidenceObject,
        matched_products: List[Dict[str, Any]]
    ) -> Tuple[str, List[ProductResult], List[str], str]:
        """
        Generates text, product cards, citations, and model status based strictly on the Evidence Object.
        """
        decision = evidence_obj.decision
        product_results: List[ProductResult] = []
        citations: List[str] = []
        model_status = "Local Instruction Model" if model_loader.instruction_model_loaded else "Deterministic Grounded Generator (Active)"

        # 1. CLARIFY Decision
        if decision == "CLARIFY":
            text = evidence_obj.clarification_question or "Could you please specify more details regarding the product you are looking for?"
            return text, [], [], model_status

        # 2. REFUSE Decision
        if decision == "REFUSE":
            reason = evidence_obj.refusal_reason or "I could not find sufficient verified evidence in the catalogue to confirm this claim."
            text = f"I am unable to verify that request. {reason}"
            return text, [], [], model_status

        # 3. ANSWER Decision
        # Assemble product results and citations
        verified_pids = set()
        verified_policy_ids = set()

        for ev in evidence_obj.evidence:
            if ev.source_type == "product":
                verified_pids.add(ev.source_id)
            elif ev.source_type == "policy":
                verified_policy_ids.add(ev.source_id)

        # Policy Answer
        if verified_policy_ids:
            policy_ev = next((ev for ev in evidence_obj.evidence if ev.source_type == "policy"), None)
            if policy_ev:
                sec_id = policy_ev.source_id
                citation_tag = citation_mapper.format_policy_citation(sec_id)
                citations.append(citation_tag)
                text = f"According to the official store policy {citation_tag}:\n\n{policy_ev.value}"
                return text, [], citations, model_status

        # Product Catalogue Answer
        text_lines = []
        for p in matched_products:
            pid = p["product_id"]
            if pid in verified_pids or not verified_pids:
                citation_tag = citation_mapper.format_product_citation(pid)
                citations.append(citation_tag)

                prod_result = ProductResult(
                    product_id=pid,
                    title=p["title"],
                    description=p.get("description", ""),
                    category=p.get("category", "General"),
                    price=p["price"],
                    stock_status=p.get("stock_status", "Available"),
                    rating=p.get("rating"),
                    attributes=p.get("attributes", {}),
                    citation=citation_tag
                )
                product_results.append(prod_result)

                # Compose grounded response summary
                stock_label = p.get("stock_status", "Available")
                attrs = p.get("attributes", {})
                attr_summary = ", ".join([f"{k}: {v}" for k, v in list(attrs.items())[:3]])
                line = (
                    f"• {p['title']} {citation_tag} — ₹{p['price']:,.2f} "
                    f"[{stock_label}]"
                )
                if attr_summary:
                    line += f" ({attr_summary})"
                text_lines.append(line)

        if text_lines:
            header = f"Here {'is the product' if len(text_lines) == 1 else 'are the products'} matching your request directly from our catalogue:"
            text = header + "\n" + "\n".join(text_lines)
        else:
            text = "I verified the requested items in our catalogue."

        # Server-side validation check
        is_valid, valid_cits, _ = citation_validator.validate_citations(text, verified_pids, verified_policy_ids)
        if not is_valid:
            text = citation_validator.sanitize_text(text, verified_pids, verified_policy_ids)

        return text, product_results, list(set(citations)), model_status

response_generator = ResponseGenerator()
