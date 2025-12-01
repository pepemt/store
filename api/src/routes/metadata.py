"""
Metadata cache endpoints for frontend.
Provides cached store metadata for filters, autocomplete, and fast category loading.
"""

import sys
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Add agents directory to path
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents')
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

from metadata_cache import get_metadata_cache

router = APIRouter()


class MetadataResponse(BaseModel):
    """Cached store metadata for frontend use."""
    categories: List[str]
    departments: List[str]
    product_groups: List[str]
    colors: List[str]
    last_refresh: Optional[str] = None


@router.get("/", response_model=MetadataResponse)
async def get_metadata():
    """
    Get cached store metadata.

    Returns categories, departments, product groups, and colors
    from a cached source (refreshed every 24 hours).

    Useful for:
    - Populating filter dropdowns
    - Autocomplete suggestions
    - Fast category loading on /products page
    """
    try:
        cache = get_metadata_cache()
        await cache.refresh()
        data = await cache.get_all_metadata()

        return MetadataResponse(
            categories=data.get("categories", []),
            departments=data.get("departments", []),
            product_groups=data.get("product_groups", []),
            colors=data.get("colors", []),
            last_refresh=cache.last_refresh.isoformat() if cache.last_refresh else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener metadata: {str(e)}",
        )
