from typing import List, Dict, Any

class EvaluationMetrics:
    """Computes rigorous RAG and shopping assistant evaluation metrics."""

    @staticmethod
    def calculate(results: List[Dict[str, Any]]) -> Dict[str, float]:
        if not results:
            return {
                "groundedness_score": 0.0,
                "answer_helpfulness_score": 0.0,
                "refusal_accuracy": 0.0,
                "clarification_accuracy": 0.0,
                "unsupported_claim_rate": 0.0,
                "citation_validity_rate": 0.0,
                "avg_latency_ms": 0.0
            }

        total = len(results)
        valid_citations_count = sum(1 for r in results if r.get("citations_valid", False))
        unsupported_claims_count = sum(1 for r in results if r.get("has_unsupported_claims", False))
        latencies = [r.get("latency_ms", 0.0) for r in results]

        # Breakdown by expected decision (if provided in test dataset)
        refusal_tests = [r for r in results if r.get("expected_decision") == "REFUSE"]
        correct_refusals = sum(1 for r in refusal_tests if r.get("actual_decision") == "REFUSE")
        refusal_acc = (correct_refusals / len(refusal_tests)) if refusal_tests else 1.0

        clarify_tests = [r for r in results if r.get("expected_decision") == "CLARIFY"]
        correct_clarifications = sum(1 for r in clarify_tests if r.get("actual_decision") == "CLARIFY")
        clarify_acc = (correct_clarifications / len(clarify_tests)) if clarify_tests else 1.0

        answer_tests = [r for r in results if r.get("expected_decision") == "ANSWER"]
        correct_answers = sum(1 for r in answer_tests if r.get("actual_decision") == "ANSWER")
        answer_helpfulness = (correct_answers / len(answer_tests)) if answer_tests else 1.0

        # Groundedness: 1.0 minus unsupported claim rate
        unsupported_rate = unsupported_claims_count / total
        groundedness = max(0.0, 1.0 - unsupported_rate)

        citation_validity = valid_citations_count / total

        return {
            "groundedness_score": round(groundedness, 4),
            "answer_helpfulness_score": round(answer_helpfulness, 4),
            "refusal_accuracy": round(refusal_acc, 4),
            "clarification_accuracy": round(clarify_acc, 4),
            "unsupported_claim_rate": round(unsupported_rate, 4),
            "citation_validity_rate": round(citation_validity, 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2)
        }

evaluation_metrics = EvaluationMetrics()
