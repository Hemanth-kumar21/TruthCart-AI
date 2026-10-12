import re
from typing import List, Tuple, Optional, Any
from app.ingestion.policy_loader import policy_loader, PolicySection

POLICY_TOPIC_KEYWORDS = {
    "RETURNS": ["return", "returns", "exchange", "refund", "refunds", "cancel", "cancellation", "replace", "replacement", "final sale", "hygiene"],
    "SHIPPING": ["shipping", "ship", "delivery", "delivered", "deliver", "delivering", "dispatch", "courier", "express", "standard", "pincode", "pin code", "fee", "charges", "rates", "free shipping", "timeline", "shipment"],
    "WARRANTY": ["warranty", "guarantee", "defect", "defects", "hardware", "liquid damage", "physical drop", "invoice", "claim", "repair"]
}

class PolicySearchEngine:
    """Retrieves grounded policy sections strictly matching shopper policy questions."""

    @staticmethod
    def detect_policy_topic(query: str) -> Optional[str]:
        q_lower = query.lower()
        topic_scores = {"RETURNS": 0, "SHIPPING": 0, "WARRANTY": 0}

        for topic, keywords in POLICY_TOPIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                    topic_scores[topic] += 1

        best_topic = max(topic_scores, key=topic_scores.get)
        if topic_scores[best_topic] > 0:
            return best_topic
        return None

    def search(self, query: str) -> List[Tuple[PolicySection, float]]:
        """Searches policy document sections based on topic detection and keyword overlap."""
        if not policy_loader.is_ready:
            return []

        q_lower = query.lower()
        topic = self.detect_policy_topic(query)
        matches: List[Tuple[PolicySection, float]] = []

        all_sections = policy_loader.get_all_sections()

        for sec in all_sections:
            score = 0.0
            # Direct topic match
            if topic and sec.topic == topic:
                score += 2.0

            # Content keyword matches
            sec_text_lower = f"{sec.title} {sec.content}".lower()
            q_words = re.findall(r'\b[a-zA-Z]{3,}\b', q_lower)
            matched_words = 0
            for w in q_words:
                if w in sec_text_lower:
                    matched_words += 1

            if q_words:
                score += (matched_words / len(q_words)) * 1.5

            if score > 0.6:
                matches.append((sec, score))

        # Sort descending by score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

policy_search_engine = PolicySearchEngine()
