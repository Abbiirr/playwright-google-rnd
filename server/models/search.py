# models/search.py

"""
Search-related data models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class SearchMode(str, Enum):
    SESSION = "session"
    SIMPLE = "simple"


class OrganicResult(BaseModel):
    position: int
    title: str
    link: str
    domain: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[str] = None
    rating: Optional[str] = None
    sitelinks: Optional[List[Dict[str, str]]] = None


class VideoResult(BaseModel):
    title: str
    duration: Optional[str] = None
    source: Optional[str] = None


class LocalResult(BaseModel):
    name: str
    rating: Optional[str] = None
    reviews: Optional[str] = None
    address: Optional[str] = None


class AdResult(BaseModel):
    title: str
    display_url: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


class FeaturedSnippet(BaseModel):
    text: str
    source: Optional[str] = None


class SearchMetadata(BaseModel):
    result_stats: Optional[str] = None
    url: Optional[str] = None
    search_time: Optional[float] = None


class SearchData(BaseModel):
    query: str
    timestamp: str
    search_metadata: Optional[SearchMetadata] = None
    organic_results: List[OrganicResult] = []
    people_also_ask: List[str] = []
    related_searches: List[str] = []
    featured_snippet: Optional[FeaturedSnippet] = None
    knowledge_panel: Optional[Dict[str, Any]] = None
    ads: List[AdResult] = []
    local_results: List[LocalResult] = []
    video_results: List[VideoResult] = []
    news_results: List[Dict[str, Any]] = []
    shopping_results: List[Dict[str, Any]] = []
    error: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query", min_length=1)
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of results")
    mode: SearchMode = Field(SearchMode.SESSION, description="Search mode (session/simple)")
    headless: bool = Field(True, description="Run browser in headless mode")
    save_to_file: bool = Field(False, description="Save results to JSON file")
    profile_name: str = Field("api_google_profile", description="Browser profile name from browser_profiles directory")


class BatchSearchRequest(BaseModel):
    queries: List[str] = Field(..., description="List of search queries", min_items=1)
    max_results: int = Field(20, ge=1, le=100, description="Maximum results per query")
    mode: SearchMode = Field(SearchMode.SESSION, description="Search mode")
    headless: bool = Field(True, description="Run browser in headless mode")
    delay_min: int = Field(5, ge=1, description="Minimum delay between searches (seconds)")
    delay_max: int = Field(10, ge=1, description="Maximum delay between searches (seconds)")
    profile_name: str = Field("api_google_profile", description="Browser profile name from browser_profiles directory")


class SearchResponse(BaseModel):
    success: bool
    query: str
    timestamp: str
    results_count: int
    data: Dict[str, Any]  # Will contain SearchData as dict
    error: Optional[str] = None


class BatchSearchResponse(BaseModel):
    success: bool
    total_queries: int
    completed: int
    results: List[SearchResponse]
    job_id: Optional[str] = None