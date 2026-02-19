# config/state.py
"""
LangGraph State Schema for Job Hunter Agent
"""

from typing import TypedDict, List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel


class JobListing(BaseModel):
    """Structured job listing from scraper"""
    job_id: str
    title: str
    company: str
    location: str
    work_mode: str                # Remote / Hybrid / Onsite
    job_url: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str]
    posted_date: Optional[str]
    experience_required: str
    salary_range: Optional[str]
    source: str                   # linkedin / indeed / internshala / etc.
    joining_date_flexible: bool   # Can join after May 16?
    relevance_score: float = 0.0


class ResumeVersion(BaseModel):
    """Tailored resume per job"""
    job_id: str
    version_id: str
    keywords_added: List[str]
    bullets_modified: List[str]
    skills_reordered: List[str]
    resume_content: Dict[str, Any]   # Full resume as structured dict
    ats_score: float


class CoverLetter(BaseModel):
    """Generated cover letter"""
    job_id: str
    content: str
    word_count: int


class ApplicationRecord(BaseModel):
    """Single application tracking record"""
    job_id: str
    company: str
    role: str
    location: str
    work_mode: str
    job_url: str
    applied: bool = False
    resume_version_id: str = ""
    applied_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    status: str = "Discovered"   # Discovered / Applied / Followed Up / Interview / Rejected / Offered
    notes: str = ""


# ─────────────────────────────────────────────
# 🔁 LANGGRAPH STATE
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    """Main state passed between LangGraph nodes"""

    # Input
    search_queries: List[str]
    candidate_skills: List[str]
    available_from: date

    # Node 1: Job Discovery
    raw_jobs: List[Dict]
    filtered_jobs: List[JobListing]

    # Node 2: Relevance Scoring
    scored_jobs: List[JobListing]
    selected_jobs: List[JobListing]

    # Node 3: Resume Optimization
    resume_versions: List[ResumeVersion]

    # Node 4: Cover Letter Generation
    cover_letters: List[CoverLetter]

    # Node 5: Application Tracker
    application_records: List[ApplicationRecord]
    tracker_export_path: str

    # Control flow
    current_job_index: int
    errors: List[str]
    run_summary: Dict[str, Any]
