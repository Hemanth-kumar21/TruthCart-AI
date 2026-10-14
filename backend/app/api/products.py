from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import require_owner, optional_current_user
from app.core.logging_config import SafeLogger
from app.db.database import db
from app.ingestion.catalogue_loader import catalogue_loader
from app.retrieval.semantic_search import local_vector_index
from app.schemas.request import ProductUpdateRequest

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("")
def list_products(
    category: Optional[str] = Query(None, description="Category filter"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum price filter"),
    in_stock_only: bool = Query(False, description="Filter for in-stock items only"),
    search: Optional[str] = Query(None, description="Search term in title, description, SKU"),
    sort_by: Optional[str] = Query("title_asc", description="Sorting criterion"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    demo: Optional[bool] = Query(None, description="Explicit demo isolation flag"),
    user: Optional[dict] = Depends(optional_current_user)
) -> Dict[str, Any]:
    """
    Customer & Owner Product Browse:
    Retrieves verified products from the currently active catalogue using real database filters.
    When demo=true or in a demo session, returns strictly isolated predefined demo products.
    Never invents unlisted products or features.
    """
    user_dict = user if isinstance(user, dict) else None
    if demo is True or (user_dict and user_dict.get("is_demo")):
        from app.core.demo_data import DEMO_PRODUCTS
        items = list(DEMO_PRODUCTS)
        if category:
            cat_lower = category.strip().lower()
            items = [p for p in items if p["category"].lower() == cat_lower]
        if min_price is not None:
            items = [p for p in items if p["price"] >= min_price]
        if max_price is not None:
            items = [p for p in items if p["price"] <= max_price]
        if in_stock_only:
            items = [p for p in items if "in stock" in p["stock_status"].lower() or "low stock" in p["stock_status"].lower()]
        if search:
            q = search.strip().lower()
            items = [
                p for p in items
                if q in p["title"].lower() or q in p["description"].lower() or q in p["product_id"].lower()
            ]
        if sort_by == "price_asc":
            items.sort(key=lambda x: x["price"])
        elif sort_by == "price_desc":
            items.sort(key=lambda x: x["price"], reverse=True)
        elif sort_by == "rating_desc":
            items.sort(key=lambda x: x.get("rating", 0) or 0, reverse=True)
        elif sort_by == "title_desc":
            items.sort(key=lambda x: x["title"], reverse=True)
        else:
            items.sort(key=lambda x: x["title"])

        all_categories = sorted(list({p["category"] for p in DEMO_PRODUCTS}))
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "categories": all_categories,
            "products": items[offset: offset + limit]
        }

    if catalogue_loader.is_synthetic_fixture:
        from app.retrieval.structured_search import structured_search_engine
        prods = structured_search_engine.search(
            category=category,
            min_price=min_price,
            max_price=max_price,
            stock_required=in_stock_only,
            keyword=search
        )
        if sort_by == "price_asc":
            prods.sort(key=lambda x: x["price"])
        elif sort_by == "price_desc":
            prods.sort(key=lambda x: x["price"], reverse=True)
        elif sort_by == "rating_desc":
            prods.sort(key=lambda x: x.get("rating", 0) or 0, reverse=True)
        elif sort_by == "title_desc":
            prods.sort(key=lambda x: x["title"], reverse=True)
        else:
            prods.sort(key=lambda x: x["title"])
    else:
        prods = db.get_active_products(
            category=category,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only,
            search_query=search,
            sort_by=sort_by
        )
    total = len(prods)
    paginated = prods[offset: offset + limit]

    if catalogue_loader.is_synthetic_fixture:
        active_categories = sorted(list({p.get("category") for p in catalogue_loader.get_all_products() if p.get("category")}))
    else:
        active_categories = db.get_active_categories()
    if not active_categories:
        active_categories = sorted(list({p.get("category") for p in prods if p.get("category")}))

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "categories": active_categories,
        "products": paginated
    }

@router.get("/{product_id}")
def get_product(product_id: str) -> Dict[str, Any]:
    """Retrieves exact verified specifications of an active product."""
    if product_id.startswith("DEMO-"):
        from app.core.demo_data import DEMO_PRODUCTS
        found = next((p for p in DEMO_PRODUCTS if p["product_id"] == product_id), None)
        if found:
            return found
    prod = db.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found in active catalogue.")
    return prod

@router.post("", response_model=Dict[str, Any])
def add_product(
    prod_data: Dict[str, Any],
    current_owner: dict = Depends(require_owner)
) -> Dict[str, Any]:
    """
    Owner adds a new verified product to the active catalogue.
    Strictly restricted to verified store owners; blocked in demo mode.
    """
    if current_owner.get("is_demo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode Protection: Adding new products to the official catalogue is restricted in demo sessions. Log in with a verified store owner account."
        )

    pid = str(prod_data.get("product_id", "")).strip()
    if not pid:
        raise HTTPException(status_code=400, detail="product_id is required.")

    existing = db.get_product_by_id(pid)
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with ID '{pid}' already exists in active catalogue.")

    created = db.create_single_product(prod_data, actor_id=current_owner["id"])
    catalogue_loader.load_from_database()
    local_vector_index.build_index(force_rebuild=True)

    SafeLogger.info(f"Owner {current_owner.get('email')} added new product {pid} to official catalogue.")
    return created

@router.put("/{product_id}")
def update_product_verified(
    product_id: str,
    req: ProductUpdateRequest,
    current_owner: dict = Depends(require_owner)
) -> Dict[str, Any]:
    """
    Owner Verified Correction:
    Updates official ground-truth product attributes after owner verification.
    Audits the update, records before/after values, and refreshes the retrieval index.
    """
    if current_owner.get("is_demo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode Protection: Modifying official product catalogue records is restricted in demo sessions. Log in with a verified store owner account to apply permanent corrections."
        )

    existing = db.get_product_by_id(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found in active catalogue.")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No field updates provided.")

    updated_prod = db.update_product(product_id, updates, actor_id=current_owner["id"])

    # Synchronize in-memory engine and search indexes
    catalogue_loader.load_from_database()
    local_vector_index.build_index(force_rebuild=True)

    SafeLogger.info(f"Owner {current_owner.get('email')} updated product {product_id}. Knowledge base refreshed.")
    return {
        "status": "success",
        "message": f"Product {product_id} updated and knowledge base refreshed.",
        "product": updated_prod
    }

@router.delete("/{product_id}")
def archive_product(
    product_id: str,
    current_owner: dict = Depends(require_owner)
) -> Dict[str, Any]:
    """Owner deactivates/archives product from active catalogue."""
    if current_owner.get("is_demo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode Protection: Archiving official product records is restricted in demo sessions. Log in with a verified store owner account."
        )

    success = db.archive_product(product_id, actor_id=current_owner["id"])
    if not success:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' could not be archived.")

    catalogue_loader.load_from_database()
    local_vector_index.build_index(force_rebuild=True)

    SafeLogger.info(f"Owner {current_owner.get('email')} archived product {product_id}.")
    return {"status": "success", "message": f"Product {product_id} archived successfully."}
