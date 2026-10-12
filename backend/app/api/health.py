from fastapi import APIRouter
from app.core.config import settings
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.policy_loader import policy_loader
from app.llm.model_loader import model_loader
from app.schemas.response import HealthResponse, ReadinessStatus

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    cat_status = catalogue_loader.get_status()
    pol_status = policy_loader.get_status()
    mod_status = model_loader.get_status()

    is_synthetic = cat_status["is_synthetic_fixture"] or pol_status["is_synthetic_fixture"]
    
    if cat_status["is_official"] and pol_status["is_official"]:
        msg = "Official Hackathon Data Active"
    elif is_synthetic:
        msg = "Running with Synthetic Development Fixtures"
    elif not cat_status["is_ready"] and not pol_status["is_ready"]:
        msg = "Awaiting Organiser Catalogue and Policy"
    elif not cat_status["is_ready"]:
        msg = "Awaiting Organiser Catalogue"
    else:
        msg = "Awaiting Organiser Policy"

    readiness = ReadinessStatus(
        catalogue_ready=cat_status["is_ready"],
        policy_ready=pol_status["is_ready"],
        embedding_model_ready=mod_status["embedding_model_ready"],
        instruction_model_ready=mod_status["instruction_model_ready"],
        is_using_synthetic_fixtures=is_synthetic,
        message=msg
    )

    return HealthResponse(
        status="ok",
        project_name=settings.PROJECT_NAME,
        team_name=settings.TEAM_NAME,
        version=settings.VERSION,
        data_readiness=readiness,
        model_readiness=mod_status
    )
