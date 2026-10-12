import re
from typing import List, Tuple, Set

class CitationMapper:
    """Utilities for generating and parsing standardized citation markers."""

    @staticmethod
    def format_product_citation(product_id: str) -> str:
        return f"[PRODUCT:{product_id.strip()}]"

    @staticmethod
    def format_policy_citation(section_id: str) -> str:
        sec = section_id.strip()
        if not sec.startswith("POLICY:"):
            sec = f"POLICY:{sec}"
        return f"[{sec}]"

    @staticmethod
    def extract_citations(text: str) -> List[Tuple[str, str]]:
        """
        Extracts all citation tags from text.
        Returns list of tuples: (source_type, source_id)
        Example: [('[PRODUCT:TC-DEV-101]', 'PRODUCT', 'TC-DEV-101'), ...]
        """
        pattern = r'\[(PRODUCT|POLICY):([^\]]+)\]'
        matches = re.findall(pattern, text)
        return [(m[0].lower(), m[1].strip()) for m in matches]

    @staticmethod
    def get_citation_strings(text: str) -> List[str]:
        """Extracts complete citation markers as strings e.g. ['[PRODUCT:TC-DEV-101]']."""
        pattern = r'(\[(?:PRODUCT|POLICY):[^\]]+\])'
        return re.findall(pattern, text)

citation_mapper = CitationMapper()
