# routers/job_router.py

"""
Job Management API Routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from server.models.job import JobStatus
from server.models.search import BatchSearchRequest, SearchResponse
from server.services.job_service import JobService
from server.services.search_service import SearchService

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])
job_service = JobService()
search_service = SearchService()


@router.post("/batch-async")
async def create_batch_job(
        request: BatchSearchRequest,
        background_tasks: BackgroundTasks
):
    """Start batch search as background job"""
    job_id = job_service.create_job(request)

    background_tasks.add_task(
        run_batch_search_background,
        job_id,
        request
    )

    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Batch search started for {len(request.queries)} queries"
    }


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of async batch search job"""
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.delete("")
async def clear_completed_jobs():
    """Clear all completed jobs from memory"""
    cleared_count = job_service.clear_completed_jobs()
    active_count = job_service.get_active_jobs_count()

    return {
        "message": f"Cleared {cleared_count} completed jobs",
        "active_jobs": active_count
    }


async def run_batch_search_background(job_id: str, request: BatchSearchRequest):
    """Background task for batch search"""
    try:
        results = []

        for i, query in enumerate(request.queries):
            job_service.update_job_progress(job_id, i, len(request.queries))

            result = await search_service.search_single(
                query=query,
                max_results=request.max_results,
                mode=request.mode,
                headless=request.headless
            )

            results.append(result.dict())

            # Delay between searches
            if i < len(request.queries) - 1:
                import asyncio
                import random
                delay = random.randint(request.delay_min, request.delay_max)
                await asyncio.sleep(delay)

        job_service.complete_job(job_id, results)

    except Exception as e:
        job_service.fail_job(job_id, str(e))