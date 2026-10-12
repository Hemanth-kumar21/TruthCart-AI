import time
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.logging_config import SafeLogger
from app.llm.query_understanding import query_understanding
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.evidence_engine.decision_engine import decision_engine
from app.evidence_engine.citation_validator import citation_validator
from app.llm.response_generator import response_generator
from app.evaluation.metrics import evaluation_metrics
from app.evaluation.report_generator import report_generator
from app.schemas.response import QuestionEvaluationResult, EvaluationReportResponse

class EvaluationPipeline:
    """Orchestrates end-to-end evaluation runs against test datasets."""

    @staticmethod
    def load_dataset(dataset_name: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
        test_dir = settings.get_test_questions_path()
        dev_dir = settings.get_dev_fixtures_path()

        # Check official test_questions dir first
        if dataset_name:
            cand_official = test_dir / dataset_name
            if cand_official.exists():
                with open(cand_official, "r", encoding="utf-8") as f:
                    return json.load(f), f"Official: {dataset_name}"

            cand_dev = dev_dir / dataset_name
            if cand_dev.exists():
                with open(cand_dev, "r", encoding="utf-8") as f:
                    return json.load(f), f"Development Fixture: {dataset_name}"

        # Search default official files
        official_files = list(test_dir.glob("*.json"))
        if official_files:
            target = official_files[0]
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f), f"Official: {target.name}"

        # Search default fixture files
        fixture_file = dev_dir / "sample_eval_questions.json"
        if fixture_file.exists():
            with open(fixture_file, "r", encoding="utf-8") as f:
                return json.load(f), "Development Fixture: sample_eval_questions.json"

        return [], "No dataset found"

    def run_evaluation(
        self,
        dataset_name: Optional[str] = None,
        max_questions: Optional[int] = None,
        dry_run: bool = False
    ) -> EvaluationReportResponse:
        questions, dataset_source = self.load_dataset(dataset_name)

        if not questions:
            report_id = str(uuid.uuid4())
            return EvaluationReportResponse(
                report_id=report_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                dataset_name="Awaiting official test questions",
                total_questions_tested=0,
                successfully_evaluated=0,
                groundedness_score=0.0,
                answer_helpfulness_score=0.0,
                refusal_accuracy=0.0,
                clarification_accuracy=0.0,
                unsupported_claim_rate=0.0,
                citation_validity_rate=0.0,
                avg_latency_ms=0.0,
                compute_info={"device": "CPU", "offline": True},
                details=[]
            )

        if max_questions:
            questions = questions[:max_questions]

        detailed_results: List[QuestionEvaluationResult] = []
        raw_eval_items: List[Dict[str, Any]] = []

        start_all = time.perf_counter()

        for q_item in questions:
            qid = str(q_item.get("question_id", f"Q-{len(detailed_results)+1}"))
            query_str = str(q_item.get("query", ""))
            expected_dec = q_item.get("expected_decision")

            t0 = time.perf_counter()

            # Pipeline execution
            parsed = query_understanding.parse(query_str)
            product_cands, policy_cand = hybrid_retriever.retrieve(query_str, parsed)
            evidence_obj = decision_engine.evaluate(query_str, parsed, product_cands, policy_cand)

            matched_prods = [c.data for c in product_cands]
            response_text, products, citations, _ = response_generator.generate_response(evidence_obj, matched_prods)

            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Citation validation
            verified_pids = {ev.source_id for ev in evidence_obj.evidence if ev.source_type == "product"}
            verified_pol_ids = {ev.source_id for ev in evidence_obj.evidence if ev.source_type == "policy"}
            is_valid_cit, _, invalid_cits = citation_validator.validate_citations(
                response_text, verified_pids, verified_pol_ids
            )

            # Check if actual decision matches expected
            actual_dec = evidence_obj.decision
            dec_match = (actual_dec == expected_dec) if expected_dec else None

            # Check unsupported claims: any invalid citation OR refusal when answer was claimed without evidence
            has_unsupported = len(invalid_cits) > 0 or len(evidence_obj.unsupported_fields) > 0

            res = QuestionEvaluationResult(
                question_id=qid,
                query=query_str,
                expected_decision=expected_dec,
                actual_decision=actual_dec,
                decision_match=dec_match,
                citations=citations,
                citations_valid=is_valid_cit,
                has_unsupported_claims=has_unsupported,
                latency_ms=round(latency_ms, 2),
                notes=q_item.get("notes")
            )
            detailed_results.append(res)
            raw_eval_items.append(res.model_dump())

        metrics = evaluation_metrics.calculate(raw_eval_items)
        report_id = str(uuid.uuid4())

        report_response = EvaluationReportResponse(
            report_id=report_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            dataset_name=dataset_source,
            total_questions_tested=len(detailed_results),
            successfully_evaluated=len(detailed_results),
            groundedness_score=metrics["groundedness_score"],
            answer_helpfulness_score=metrics["answer_helpfulness_score"],
            refusal_accuracy=metrics["refusal_accuracy"],
            clarification_accuracy=metrics["clarification_accuracy"],
            unsupported_claim_rate=metrics["unsupported_claim_rate"],
            citation_validity_rate=metrics["citation_validity_rate"],
            avg_latency_ms=metrics["avg_latency_ms"],
            compute_info={
                "device": "CPU",
                "offline": True,
                "total_run_time_sec": round(time.perf_counter() - start_all, 2)
            },
            details=detailed_results
        )

        if not dry_run:
            report_generator.save_report(report_response.model_dump())

        return report_response

from typing import Tuple
evaluation_pipeline = EvaluationPipeline()
