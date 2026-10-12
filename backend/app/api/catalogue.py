from fastapi import APIRouter
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.policy_loader import policy_loader
from app.retrieval.semantic_search import local_vector_index
from app.schemas.response import CatalogueStatusResponse
from app.schemas.request import CatalogueIngestRequest

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])

@router.get("/status", response_model=CatalogueStatusResponse)
def get_catalogue_status() -> CatalogueStatusResponse:
    status_info = catalogue_loader.get_status()
    return CatalogueStatusResponse(
        status=status_info["status"],
        is_official=status_info["is_official"],
        is_synthetic_fixture=status_info["is_synthetic_fixture"],
        records_loaded=status_info["records_loaded"],
        records_rejected=status_info["records_rejected"],
        duplicate_records=status_info["duplicate_records"],
        missing_fields_count=status_info["missing_fields_count"],
        categories=status_info["categories"],
        total_active_products=status_info["total_active_products"],
        data_source_path=status_info["data_source_path"]
    )

@router.post("/reload", response_model=CatalogueStatusResponse)
def reload_catalogue(req: CatalogueIngestRequest = CatalogueIngestRequest()) -> CatalogueStatusResponse:
    """Reloads catalogue from disk. Supports force-fixtures for dev/testing."""
    catalogue_loader.load_default_catalogue(force_fixtures=req.use_synthetic)
    policy_loader.load_default_policy(force_fixtures=req.use_synthetic)
    local_vector_index.build_index(force_rebuild=True)
    return get_catalogue_status()
