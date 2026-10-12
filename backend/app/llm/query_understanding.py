import re
from typing import Dict, Any, List, Optional
from app.retrieval.policy_search import policy_search_engine

class QueryUnderstanding:
    """Deterministic natural-language and code-mixed query parser with structured entity extraction."""

    # Common categories
    KNOWN_CATEGORIES = {
        "shirt": "Apparel",
        "shirts": "Apparel",
        "tshirt": "Apparel",
        "t-shirt": "Apparel",
        "pants": "Apparel",
        "jeans": "Apparel",
        "shoes": "Footwear",
        "shoe": "Footwear",
        "sneakers": "Footwear",
        "running shoes": "Footwear",
        "laptop": "Electronics",
        "laptops": "Electronics",
        "headphone": "Electronics",
        "headphones": "Electronics",
        "earphones": "Electronics"
    }

    KNOWN_COLORS = ["blue", "sky blue", "navy blue", "navy", "white", "black", "red", "green", "cobalt blue", "grey", "gray"]
    KNOWN_MATERIALS = ["cotton", "linen", "silk", "leather", "polyester", "wool"]
    KNOWN_BRANDS = ["talentcloth", "aerostep", "apextech", "zensound", "apple", "samsung", "nike", "adidas"]

    @staticmethod
    def parse_budget(text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parses price constraints including 'under 2k', 'below 1500', 'between 1000 and 2000'."""
        max_price = None
        min_price = None

        t = text.lower()

        # Handle 'k' multiplier e.g. '2k' -> '2000'
        t = re.sub(r'(\d+)\s*k\b', lambda m: str(int(m.group(1)) * 1000), t)

        # 1. Between X and Y
        between_match = re.search(r'between\s+(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', t)
        if between_match:
            min_price = float(between_match.group(1))
            max_price = float(between_match.group(2))
            return min_price, max_price

        # 2. Under / Below / Less than
        under_match = re.search(r'(?:under|below|less\s+than|budget(?:\s+is)?|max|up\s+to|<=|<)\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', t)
        if under_match:
            max_price = float(under_match.group(1))

        # 3. Above / Over / More than
        above_match = re.search(r'(?:above|over|more\s+than|min|at\s+least|>=|>)\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', t)
        if above_match:
            min_price = float(above_match.group(1))

        # 4. Trailing "under 1000" or plain numbers if preceded by category
        if max_price is None and min_price is None:
            plain_under = re.search(r'\b(?:under|sub)\s*(\d+)', t)
            if plain_under:
                max_price = float(plain_under.group(1))

        return min_price, max_price

    @staticmethod
    def extract_product_id(text: str) -> Optional[str]:
        """Detects standard product IDs like TC-DEV-101, P102, TC-101, SKU-1234."""
        # Match explicit pattern
        id_match = re.search(r'\b(?:product|id|item|sku)?\s*([A-Za-z]{1,4}-\w+-\d+|\b[A-Za-z]{1,3}\d{2,6}\b)', text, flags=re.IGNORECASE)
        if id_match:
            cand = id_match.group(1).strip()
            # Exclude false positives like '2k', '16gb', '40h'
            if not re.match(r'^\d+[a-zA-Z]+$', cand) and not cand.lower() in ("ram", "ssd", "usb"):
                return cand.upper()
        return None

    @classmethod
    def parse(cls, query: str) -> Dict[str, Any]:
        """Extracts search constraints and intent deterministically."""
        cleaned = query.strip()
        q_lower = cleaned.lower()

        # Handle code-mixed Telugu/Hindi keywords like 'kavali' (want) or 'chahiye' (want)
        normalized_q = q_lower.replace("kavali", "").replace("chahiye", "").replace("please", "")

        pid = cls.extract_product_id(cleaned)
        min_p, max_p = cls.parse_budget(normalized_q)

        # Detect category
        category = None
        for cat_kw, mapped_cat in cls.KNOWN_CATEGORIES.items():
            if re.search(r'\b' + re.escape(cat_kw) + r'\b', normalized_q):
                category = mapped_cat
                break

        # Detect color
        color = None
        for c in cls.KNOWN_COLORS:
            if re.search(r'\b' + re.escape(c) + r'\b', normalized_q):
                color = c.title()
                break

        # Detect material
        material = None
        for m in cls.KNOWN_MATERIALS:
            if re.search(r'\b' + re.escape(m) + r'\b', normalized_q):
                material = m.title()
                break

        # Detect brand
        brand = None
        for b in cls.KNOWN_BRANDS:
            if re.search(r'\b' + re.escape(b) + r'\b', normalized_q):
                brand = b.title()
                break

        # Detect stock requirement
        stock_required = None
        if any(term in normalized_q for term in ["in stock", "available", "ready to ship", "can i buy"]):
            stock_required = True

        # Detect policy topic
        policy_topic = policy_search_engine.detect_policy_topic(cleaned)
        is_policy = policy_topic is not None and not pid and not max_p

        # Detect specific requested attributes
        requested_attrs = []
        if "price" in normalized_q or "cost" in normalized_q or "rate" in normalized_q:
            requested_attrs.append("price")
        if "ram" in normalized_q:
            requested_attrs.append("ram")
        if "storage" in normalized_q or "ssd" in normalized_q or "hdd" in normalized_q:
            requested_attrs.append("storage")
        if "battery" in normalized_q:
            requested_attrs.append("battery_life")
        if "material" in normalized_q:
            requested_attrs.append("material")
        if "color" in normalized_q:
            requested_attrs.append("color")

        intent = "search"
        if is_policy:
            intent = "policy"
        elif pid and requested_attrs:
            intent = "attribute_lookup"
        elif pid:
            intent = "product_lookup"

        return {
            "query": cleaned,
            "intent": intent,
            "product_id": pid,
            "category": category,
            "min_price": min_p,
            "max_price": max_p,
            "color": color,
            "material": material,
            "brand": brand,
            "stock_required": stock_required,
            "policy_topic": policy_topic,
            "is_policy_query": is_policy,
            "requested_attributes": requested_attrs
        }

from typing import Tuple
query_understanding = QueryUnderstanding()
