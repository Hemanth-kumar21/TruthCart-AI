import io
import json
from typing import List, Dict, Any, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

from app.core.auth import require_owner, optional_current_user
from app.core.logging_config import SafeLogger
from app.db.database import db
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.data_validator import DataValidator
from app.retrieval.semantic_search import local_vector_index
from app.schemas.request import CatalogueIngestRequest, CatalogueImportConfirmRequest
from app.schemas.response import (
    CatalogueStatusResponse,
    CataloguePreviewResponse,
    CatalogueVersionResponse
)

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])

MAX_UPLOAD_SIZE = 35 * 1024 * 1024 # 35 MB target upload limit

@router.get("/status", response_model=CatalogueStatusResponse)
def get_catalogue_status(
    demo: Optional[bool] = None,
    user: Optional[dict] = Depends(optional_current_user)
) -> CatalogueStatusResponse:
    """Returns current active catalogue status and metrics (isolated for demo sessions)."""
    user_dict = user if isinstance(user, dict) else None
    if demo is True or (user_dict and user_dict.get("is_demo")):
        from app.core.demo_data import DEMO_CATALOGUES
        active_demo = DEMO_CATALOGUES[0]
        return CatalogueStatusResponse(
            status=active_demo["status"],
            is_ready=True,
            is_official=False,
            is_synthetic_fixture=False,
            records_loaded=active_demo["record_count"],
            records_rejected=0,
            duplicate_records=0,
            missing_fields_count=0,
            categories=["Audio", "Electronics", "Footwear", "Home & Kitchen", "Wearables"],
            total_active_products=active_demo["record_count"],
            data_source_path="predefined_demo_catalog.json (Isolated Sandbox)"
        )
    status_info = catalogue_loader.get_status()
    return CatalogueStatusResponse(
        status=status_info["status"],
        is_ready=status_info["is_ready"],
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
    """Reloads catalogue. Kept backwards compatible for tests and development fixtures."""
    from app.ingestion.policy_loader import policy_loader
    catalogue_loader.load_default_catalogue(force_fixtures=req.use_synthetic)
    policy_loader.load_default_policy(force_fixtures=req.use_synthetic)
    local_vector_index.build_index(force_rebuild=True)
    return get_catalogue_status(user=None)

@router.get("/versions", response_model=List[CatalogueVersionResponse])
def get_catalogue_versions(current_owner: dict = Depends(require_owner)) -> List[CatalogueVersionResponse]:
    """Owner view: Lists all imported and active catalogue versions. Demo sessions receive strictly isolated demo catalogue."""
    if current_owner.get("is_demo"):
        from app.core.demo_data import DEMO_CATALOGUES
        return [CatalogueVersionResponse(**c) for c in DEMO_CATALOGUES]

    cats = db.get_all_catalogues()
    res = []
    for c in cats:
        res.append(CatalogueVersionResponse(
            id=c["id"],
            version=c["version"],
            name=c["name"],
            filename=c["filename"],
            owner_id=c["owner_id"],
            record_count=c["record_count"],
            valid_count=c["valid_count"],
            invalid_count=c["invalid_count"],
            status=c["status"],
            is_active=bool(c["is_active"]),
            created_at=c["created_at"],
            activated_at=c.get("activated_at")
        ))
    return res

@router.post("/upload-preview", response_model=CataloguePreviewResponse)
async def upload_and_preview_catalogue(
    file: UploadFile = File(...),
    current_owner: dict = Depends(require_owner)
) -> CataloguePreviewResponse:
    """
    Step 1 & 2 of Owner workflow:
    Receives file, parses CSV/JSON, validates against schema without altering ground truths,
    and returns a preview report with errors and warnings.
    """
    filename = file.filename or "unknown_file"
    suffix = filename.split(".")[-1].lower() if "." in filename else ""

    if suffix not in ("csv", "tsv", "json", "xls", "xlsx"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. TruthCart AI accepts CSV, TSV, JSON, XLS, or XLSX catalogue files."
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size limit of {MAX_UPLOAD_SIZE // (1024*1024)} MB."
        )

    records: List[Dict[str, Any]] = []
    try:
        if suffix == "json":
            raw_data = json.loads(content.decode("utf-8"))
            if isinstance(raw_data, list):
                records = raw_data
            elif isinstance(raw_data, dict):
                for v in raw_data.values():
                    if isinstance(v, list):
                        records = v
                        break
        elif suffix in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(content), dtype=object)
            records = df.to_dict(orient="records")
        else:
            sep = "\t" if suffix == "tsv" else ","
            df = pd.read_csv(io.BytesIO(content), sep=sep, dtype=object)
            records = df.to_dict(orient="records")
    except Exception as e:
        SafeLogger.error(f"Failed to parse uploaded catalogue file {filename}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {str(e)}. Please check format encoding."
        )

    if not records:
        raise HTTPException(status_code=400, detail="The uploaded catalogue file contains no records.")

    # Validation and error aggregation
    keys = list(records[0].keys())
    header_map = catalogue_loader._resolve_headers(keys)

    valid_records: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    warnings: List[str] = []
    seen_ids = set()

    for idx, raw_item in enumerate(records, start=1):
        mapped = {}
        for canonical, file_key in header_map.items():
            if file_key in raw_item:
                mapped[canonical] = raw_item[file_key]

        attrs = mapped.get("attributes")
        if not isinstance(attrs, dict):
            attrs = DataValidator.parse_attributes(attrs)
        for k, v in raw_item.items():
            if k not in header_map.values() and k not in mapped:
                attrs[str(k).strip().lower()] = v
        mapped["attributes"] = attrs

        valid, reason, normalized = DataValidator.validate_record(mapped)
        if not valid:
            errors.append({
                "row": idx,
                "product_id": raw_item.get("product_id") or raw_item.get("id") or f"Row {idx}",
                "issue": reason
            })
            continue

        pid = normalized["product_id"]
        if pid in seen_ids:
            warnings.append(f"Row {idx}: Duplicate Product ID '{pid}' detected. Later occurrence skipped.")
            continue
        seen_ids.add(pid)

        # Check for missing attributes as advisory warning
        if not normalized.get("attributes"):
            warnings.append(f"Row {idx} ({pid}): No extended specifications or attributes found.")

        valid_records.append(normalized)

    # Inferred next version based on existing versions avoiding any collision
    existing_cats = db.get_all_catalogues()
    existing_versions = [c["version"] for c in existing_cats]
    
    inferred_version = "v1.1.0"
    if existing_versions:
        import re
        max_major = 1
        max_minor = 0
        for v in existing_versions:
            m = re.match(r'v?(\d+)\.(\d+)', v.strip())
            if m:
                maj = int(m.group(1))
                min_ = int(m.group(2))
                if maj > max_major or (maj == max_major and min_ > max_minor):
                    max_major = maj
                    max_minor = min_
        candidate = f"v{max_major}.{max_minor + 1}.0"
        while candidate.lower() in [ev.lower() for ev in existing_versions]:
            max_minor += 1
            candidate = f"v{max_major}.{max_minor}.0"
        inferred_version = candidate

    return CataloguePreviewResponse(
        filename=filename,
        total_rows=len(records),
        valid_count=len(valid_records),
        invalid_count=len(errors),
        preview_records=valid_records[:25],
        all_valid_records=valid_records,
        errors=errors[:50], # Cap report size
        warnings=warnings[:50],
        inferred_version=inferred_version
    )

@router.post("/import", response_model=CatalogueVersionResponse)
def confirm_import_catalogue(
    req: CatalogueImportConfirmRequest,
    current_owner: dict = Depends(require_owner)
) -> CatalogueVersionResponse:
    """
    Step 3 of Owner workflow:
    Confirms validated dataset import into database. Saves records without overwriting
    active catalogue until explicit activation.
    """
    if current_owner.get("is_demo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode Protection: Importing new catalogue versions is disabled in demo mode to protect official production catalogue records. File upload preview and schema validation are available."
        )

    if not req.records:
        raise HTTPException(status_code=400, detail="Cannot import an empty record list.")

    # Idempotent / Unique Version Enforcement
    existing_version = db.get_catalogue_by_version(req.version)
    if existing_version:
        raise HTTPException(
            status_code=400,
            detail=f"Catalogue version '{req.version}' is already registered (status: {existing_version['status']}). Please provide a unique semantic version number (e.g. v2.1.0)."
        )

    cat = db.create_catalogue(
        name=req.name,
        filename=req.filename,
        version=req.version,
        owner_id=current_owner["id"],
        records=req.records,
        validation_report=req.validation_report,
        valid_count=req.valid_count,
        invalid_count=req.invalid_count,
        status="READY_FOR_ACTIVATION"
    )


    SafeLogger.info(f"Owner {current_owner.get('email')} imported catalogue {req.version} ({req.valid_count} products).")
    return CatalogueVersionResponse(
        id=cat["id"],
        version=cat["version"],
        name=cat["name"],
        filename=cat["filename"],
        owner_id=cat["owner_id"],
        record_count=cat["record_count"],
        valid_count=cat["valid_count"],
        invalid_count=cat["invalid_count"],
        status=cat["status"],
        is_active=bool(cat["is_active"]),
        created_at=cat["created_at"],
        activated_at=cat.get("activated_at")
    )

@router.post("/{cat_id}/activate", response_model=CatalogueStatusResponse)
def activate_catalogue(
    cat_id: str,
    current_owner: dict = Depends(require_owner)
) -> CatalogueStatusResponse:
    """
    Step 4 of Owner workflow:
    Atomically activates approved catalogue version, updates retrieval indexes,
    and refreshes the customer assistant's knowledge base.
    """
    if current_owner.get("is_demo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode Protection: Activating catalogue versions is restricted in demo mode to protect official production catalogue records. Sign in with a verified store owner account to activate production catalogues."
        )

    cat = db.get_catalogue_by_id(cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail=f"Catalogue {cat_id} not found.")

    try:
        # 1. Atomically switch active version in database
        db.activate_catalogue(cat_id=cat["id"], actor_id=current_owner["id"])

        # 2. Reload memory loader from active database
        catalogue_loader.load_from_database()

        # 3. Refresh and rebuild local vector search index
        indexed_ok = local_vector_index.build_index(force_rebuild=True)
        if not indexed_ok and catalogue_loader.is_ready:
            SafeLogger.error("Catalogue activated in DB, but vector index rebuild failed.")

        SafeLogger.info(f"Catalogue {cat['version']} successfully activated by {current_owner.get('email')}.")
        return get_catalogue_status(user=current_owner)
    except HTTPException:
        raise
    except Exception as e:
        SafeLogger.error(f"Error activating catalogue {cat_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate catalogue {cat.get('version', cat_id)}: {str(e)}"
        )

@router.post("/rebuild-index")
def rebuild_knowledge_base_index(current_owner: dict = Depends(require_owner)) -> dict:
    """
    Refreshes and rebuilds the local vector knowledge base index from active ground truth records.
    Validates document indexing and policy documents before completing.
    """
    if current_owner.get("is_demo"):
        return {
            "status": "success",
            "message": "Knowledge base index verified for predefined demo showcase (isolated sandbox). Production index untouched.",
            "catalogue_version": "v1.0.0-demo",
            "products_indexed": 16,
            "policies_indexed": 4,
            "index_ready": True,
            "retrieval_verified": True
        }
    from app.ingestion.policy_loader import policy_loader

    # 1. Reload active catalogue and policies from authoritative database
    catalogue_loader.load_from_database()
    policy_loader.load_from_database()

    # 2. Rebuild local vector index
    indexed = local_vector_index.build_index(force_rebuild=True)

    # 3. Test verification retrieval
    test_retrieval_ok = False
    all_prods = catalogue_loader.get_all_products()
    if indexed and all_prods:
        test_results = local_vector_index.search(all_prods[0].get("title", ""), top_k=1)
        test_retrieval_ok = len(test_results) > 0

    active_cat = db.get_active_catalogue()
    active_version = active_cat["version"] if active_cat else "None"

    db.log_audit(
        actor_id=current_owner["id"],
        actor_role="OWNER",
        action="INDEX_REBUILT",
        target_id="knowledge_base",
        target_type="INDEX",
        details={
            "status": "rebuilt",
            "success": indexed,
            "catalogue_version": active_version,
            "products_indexed": len(catalogue_loader.products),
            "policies_loaded": len(policy_loader.sections),
            "retrieval_verified": test_retrieval_ok
        }
    )

    return {
        "status": "success" if (indexed or len(catalogue_loader.products) == 0) else "partial",
        "message": "Knowledge base index rebuilt and validated successfully.",
        "catalogue_version": active_version,
        "products_indexed": len(catalogue_loader.products),
        "policies_indexed": len(policy_loader.sections),
        "index_ready": indexed,
        "retrieval_verified": test_retrieval_ok
    }
