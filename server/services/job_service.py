# services/job_service.py

"""
Job service - handles background job management
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from server.models.job import JobStatus, JobState
from server.models.search import SearchMode, BatchSearchRequest


class JobService:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, request: BatchSearchRequest) -> str:
        """Create a new job"""
        job_id = str(uuid.uuid4())

        self.jobs[job_id] = {
            "status": JobState.STARTED,
            "progress": f"0/{len(request.queries)}",
            "results": [],
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "request": request.dict()
        }

        return job_id

    def update_job_progress(self, job_id: str, current: int, total: int):
        """Update job progress"""
        if job_id in self.jobs:
            self.jobs[job_id]["progress"] = f"{current}/{total}"
            self.jobs[job_id]["status"] = JobState.RUNNING

    def complete_job(self, job_id: str, results: list):
        """Mark job as completed"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = JobState.COMPLETED
            self.jobs[job_id]["results"] = results
            self.jobs[job_id]["completed_at"] = datetime.now().isoformat()

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = JobState.FAILED
            self.jobs[job_id]["error"] = error
            self.jobs[job_id]["completed_at"] = datetime.now().isoformat()

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get job status"""
        if job_id not in self.jobs:
            return None

        job_data = self.jobs[job_id]

        return JobStatus(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            results=job_data.get("results"),
            error=job_data.get("error"),
            created_at=job_data.get("created_at"),
            completed_at=job_data.get("completed_at")
        )

    def clear_completed_jobs(self) -> int:
        """Clear completed jobs and return count"""
        completed_count = sum(
            1 for j in self.jobs.values()
            if j["status"] == JobState.COMPLETED
        )

        self.jobs = {
            jid: data for jid, data in self.jobs.items()
            if data["status"] != JobState.COMPLETED
        }

        return completed_count

    def get_active_jobs_count(self) -> int:
        """Get count of active jobs"""
        return len(self.jobs)