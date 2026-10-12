import re
import json
from typing import Any, Dict, Optional, Tuple

class DataValidator:
    """Validates and normalizes raw product record fields without altering ground truths."""

    @staticmethod
    def parse_price(val: Any) -> Optional[float]:
        """Safely parses prices from diverse formats (numbers, currency strings) to float."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            try:
                price = float(val)
                return price if price >= 0 else None
            except (ValueError, TypeError):
                return None
        
        # String parsing
        s = str(val).strip()
        if not s or s.lower() in ("nan", "null", "none", "n/a"):
            return None
        
        # Remove currency symbols (₹, $, €, £) and commas
        cleaned = re.sub(r'[^\d.]', '', s)
        try:
            price = float(cleaned)
            return price if price >= 0 else None
        except ValueError:
            return None

    @staticmethod
    def normalize_stock_status(val: Any) -> str:
        """Normalizes stock status to standard 'In Stock' or 'Out of Stock'."""
        if val is None:
            return "Unknown"
        s = str(val).strip().lower()
        if s in ("1", "true", "in stock", "in_stock", "available", "yes"):
            return "In Stock"
        if s in ("0", "false", "out of stock", "out_of_stock", "unavailable", "no", "sold out"):
            return "Out of Stock"
        return str(val).strip()

    @staticmethod
    def parse_attributes(val: Any) -> Dict[str, Any]:
        """Parses attributes from dictionary, JSON string, or semicolon/comma key:value pairs."""
        if val is None:
            return {}
        if isinstance(val, dict):
            # Normalize keys to lowercase for robust lookup while preserving values
            return {str(k).strip().lower(): v for k, v in val.items()}
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return {}
            # Try JSON format
            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, dict):
                        return {str(k).strip().lower(): v for k, v in parsed.items()}
                except json.JSONDecodeError:
                    pass
            # Try key:value; key2:value2 format
            attrs = {}
            pairs = re.split(r'[;,]\s*', s)
            for pair in pairs:
                if ':' in pair:
                    k, v = pair.split(':', 1)
                    attrs[k.strip().lower()] = v.strip()
                elif '=' in pair:
                    k, v = pair.split('=', 1)
                    attrs[k.strip().lower()] = v.strip()
            return attrs
        return {}

    @classmethod
    def validate_record(cls, raw: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates record has required minimum fields: product_id and title.
        Preserves original raw data alongside normalized representation.
        """
        prod_id = raw.get("product_id")
        if prod_id is None or str(prod_id).strip() == "" or str(prod_id).lower() in ("nan", "none", "null"):
            return False, "Missing or empty product_id", None

        title = raw.get("title")
        if title is None or str(title).strip() == "":
            return False, "Missing or empty title", None

        raw_price = raw.get("price")
        parsed_price = cls.parse_price(raw_price)
        if parsed_price is None:
            return False, f"Invalid or missing numeric price: {raw_price}", None

        normalized = {
            "product_id": str(prod_id).strip(),
            "title": str(title).strip(),
            "description": str(raw.get("description", "")).strip(),
            "category": str(raw.get("category", "General")).strip(),
            "price": parsed_price,
            "stock_status": cls.normalize_stock_status(raw.get("stock_status")),
            "rating": float(raw.get("rating")) if raw.get("rating") is not None and str(raw.get("rating")).replace('.','',1).isdigit() else None,
            "attributes": cls.parse_attributes(raw.get("attributes")),
            "raw_record": raw # Kept for ground truth evidence tracing
        }
        return True, None, normalized
