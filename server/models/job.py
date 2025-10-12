# models/job.py

"""
Job-related data models
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class JobState(str, Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    status: JobState
    progress: str
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None