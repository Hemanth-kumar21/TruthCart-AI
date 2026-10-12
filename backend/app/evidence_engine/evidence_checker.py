from typing import Dict, Any, List, Optional
from app.schemas.response import EvidenceItem
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.policy_loader import policy_loader

class EvidenceChecker:
    """Verifies that individual factual claims correspond directly to ground truth records."""

    @staticmethod
    def extract_product_evidence(product: Dict[str, Any], requested_fields: List[str]) -> List[EvidenceItem]:
        """Extracts verified evidence items directly from catalogue record."""
        items: List[EvidenceItem] = []
        pid = product["product_id"]

        # Core fields always verified if product matched
        items.append(EvidenceItem(
            source_type="product",
            source_id=pid,
            field="title",
            value=product["title"]
        ))
        items.append(EvidenceItem(
            source_type="product",
            source_id=pid,
            field="price",
            value=f"₹{product['price']:,.2f}"
        ))
        items.append(EvidenceItem(
            source_type="product",
            source_id=pid,
            field="stock_status",
            value=product["stock_status"]
        ))

        if product.get("category"):
            items.append(EvidenceItem(
                source_type="product",
                source_id=pid,
                field="category",
                value=product["category"]
            ))

        # Check attributes
        attrs = product.get("attributes", {})
        for req in requested_fields:
            req_lower = req.lower()
            if req_lower in attrs:
                items.append(EvidenceItem(
                    source_type="product",
                    source_id=pid,
                    field=req_lower,
                    value=attrs[req_lower]
                ))
            else:
                # Check for partial key match
                for k, v in attrs.items():
                    if req_lower in k:
                        items.append(EvidenceItem(
                            source_type="product",
                            source_id=pid,
                            field=k,
                            value=v
                        ))
                        break

        return items

    @staticmethod
    def extract_policy_evidence(section_id: str, field: str, matched_text: str) -> EvidenceItem:
        return EvidenceItem(
            source_type="policy",
            source_id=section_id,
            field=field,
            value=matched_text
        )

evidence_checker = EvidenceChecker()
