# routers/search_router.py

"""
Search API Routes
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pathlib import Path
from server.models.search import (
    SearchRequest,
    SearchResponse,
    BatchSearchRequest,
    BatchSearchResponse,
    SearchMode
)
from server.services.search_service import SearchService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])
search_service = SearchService()


@router.get("/profiles")
async def list_profiles():
    """Get list of available browser profiles"""
    logger.info("GET /api/search/profiles - Listing available profiles")
    try:
        profiles_dir = Path("browser_profiles")
        if profiles_dir.exists():
            profiles = [p.name for p in profiles_dir.iterdir() if p.is_dir()]
            logger.info(f"Found {len(profiles)} profiles: {profiles}")
            return {
                "success": True,
                "profiles": profiles,
                "default": "api_google_profile"
            }
        else:
            logger.warning("browser_profiles directory not found")
            return {
                "success": False,
                "profiles": [],
                "error": "browser_profiles directory not found"
            }
    except Exception as e:
        logger.error(f"Error listing profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform a single Google search"""
    logger.info(f"POST /api/search - Received search request: query='{request.query}', profile='{request.profile_name}'")
    logger.debug(f"Request details: {request.model_dump()}")

    try:
        result = await search_service.search_single(
            query=request.query,
            max_results=request.max_results,
            mode=request.mode,
            headless=request.headless,
            save_to_file=request.save_to_file,
            profile_name=request.profile_name
        )
        logger.info(f"Search request completed: success={result.success}, results_count={result.results_count}")
        return result
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=SearchResponse)
async def search_get(
        q: str = Query(..., description="Search query"),
        max_results: int = Query(20, ge=1, le=100),
        mode: SearchMode = Query(SearchMode.SESSION),
        headless: bool = Query(True),
        profile_name: str = Query("api_google_profile", description="Browser profile name")
):
    """GET endpoint for single search - useful for testing"""
    logger.info(f"GET /api/search - Received search request: q='{q}', profile='{profile_name}'")
    logger.debug(f"Query params: max_results={max_results}, mode={mode}, headless={headless}, profile_name={profile_name}")

    request = SearchRequest(
        query=q,
        max_results=max_results,
        mode=mode,
        headless=headless,
        save_to_file=False,
        profile_name=profile_name
    )
    return await search(request)


@router.post("/batch", response_model=BatchSearchResponse)
async def batch_search(request: BatchSearchRequest):
    """Perform multiple Google searches sequentially"""
    logger.info(f"POST /api/search/batch - Received batch request: {len(request.queries)} queries, profile='{request.profile_name}'")
    logger.debug(f"Batch request details: {request.model_dump()}")

    try:
        results = await search_service.search_batch(
            queries=request.queries,
            max_results=request.max_results,
            mode=request.mode,
            headless=request.headless,
            delay_min=request.delay_min,
            delay_max=request.delay_max,
            profile_name=request.profile_name
        )

        response = BatchSearchResponse(
            success=True,
            total_queries=len(request.queries),
            completed=len(results),
            results=results
        )

        logger.info(f"Batch search completed: {response.completed}/{response.total_queries} queries processed")
        return response
    except Exception as e:
        logger.error(f"Error in batch_search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))