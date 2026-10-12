from typing import List, Dict, Any, Optional, Tuple

class AmbiguityDetector:
    """Detects ambiguous user intents, multiple candidate ties, or conflicting constraints."""

    @staticmethod
    def detect_conflicting_constraints(parsed_query: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        min_p = parsed_query.get("min_price")
        max_p = parsed_query.get("max_price")
        if min_p is not None and max_p is not None and min_p > max_p:
            return True, f"Conflicting price constraints: minimum ₹{min_p:.0f} is higher than maximum ₹{max_p:.0f}."
        return False, None

    @staticmethod
    def check_candidate_ambiguity(
        candidates: List[Dict[str, Any]],
        parsed_query: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines whether candidate matches require clarification.
        If a query is very generic and returns multiple distinct items, ask a focused clarification.
        """
        # If query specified exact product ID, it is NOT ambiguous
        if parsed_query.get("product_id"):
            return False, None

        num_matches = len(candidates)
        if num_matches == 0:
            return False, None

        # If user asked for a specific item (e.g., "Apex 15 Stealth Gaming Laptop") and exactly 1 product matched
        if num_matches == 1:
            return False, None

        # If user asked very generic category query ("shirts", "shoes", "laptop") without price/brand/attributes
        has_specific_filters = any([
            parsed_query.get("max_price"),
            parsed_query.get("min_price"),
            parsed_query.get("brand"),
            parsed_query.get("color"),
            parsed_query.get("material"),
            parsed_query.get("required_attributes")
        ])

        if not has_specific_filters and num_matches > 1:
            category = parsed_query.get("category") or "products"
            brands = sorted(list({c.get("attributes", {}).get("brand") for c in candidates if c.get("attributes", {}).get("brand")}))
            if brands:
                return True, f"I found {num_matches} {category}. Could you specify your preferred brand (e.g., {', '.join(brands[:3])}) or a target price range?"
            return True, f"I found {num_matches} options matching '{category}'. Could you specify a preferred color, material, or budget?"

        return False, None

ambiguity_detector = AmbiguityDetector()
