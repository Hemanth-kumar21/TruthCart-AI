from fastapi import APIRouter, HTTPException
from app.schemas.request import EvaluationRequest
from app.schemas.response import EvaluationReportResponse
from app.evaluation.evaluate import evaluation_pipeline
from app.core.logging_config import SafeLogger

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.post("/run", response_model=EvaluationReportResponse)
def run_evaluation_suite(req: EvaluationRequest = EvaluationRequest()) -> EvaluationReportResponse:
    try:
        report = evaluation_pipeline.run_evaluation(
            dataset_name=req.dataset_name,
            max_questions=req.max_questions,
            dry_run=req.dry_run
        )
        return report
    except Exception as e:
        SafeLogger.error(f"Error during evaluation execution: {str(e)}")
        raise HTTPException(status_code=500, detail="Evaluation execution encountered an internal error.")
