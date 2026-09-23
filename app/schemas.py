"""
Pydantic v2 schemas used for request validation and response serialization.
"""
 
from datetime import datetime
from typing import Optional, Literal
 
from pydantic import BaseModel, EmailStr, Field, ConfigDict
 
 
# ---------------------------------------------------------------------------
# Auth / User
# ---------------------------------------------------------------------------
 
class HackerRegisterRequest(BaseModel):
    account_type: Literal["hacker"] = "hacker"
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    handle: str = Field(min_length=3, max_length=64)
    bio: Optional[str] = ""
    tryhackme_url: Optional[str] = ""
    hackthebox_url: Optional[str] = ""
    github_url: Optional[str] = ""
 
 
class CompanyRegisterRequest(BaseModel):
    account_type: Literal["company"] = "company"
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=2, max_length=255)
    industry: str = Field(min_length=1, max_length=150)
    website_url: str = Field(min_length=4, max_length=500)
 
 
class LoginRequest(BaseModel):
    username: str
    password: str
 
 
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
 
 
class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    username: str
    email: str
    role: str
    reputation_score: int
    created_at: datetime
    is_verified: bool = False
    handle: Optional[str] = None
    bio: Optional[str] = None
    tryhackme_url: Optional[str] = None
    hackthebox_url: Optional[str] = None
    github_url: Optional[str] = None
    company_is_approved: Optional[bool] = None
    company_name: Optional[str] = None
 
 
# ---------------------------------------------------------------------------
# Company / Admin
# ---------------------------------------------------------------------------
 
class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    company_name: str
    industry: str
    website_url: str
    is_approved: bool
    created_at: datetime
 
 
# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------
 
class ProgramCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    target_url: str = Field(min_length=4, max_length=500)
    in_scope: str
    out_of_scope: str
    rules_of_engagement: Optional[str] = ""
    bounty_type: Literal["points", "cash"] = "points"
    reward_low: Optional[str] = ""
    reward_medium: Optional[str] = ""
    reward_high: Optional[str] = ""
    reward_critical: Optional[str] = ""
 
 
class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    company_id: int
    title: str
    target_url: str
    in_scope: str
    out_of_scope: str
    rules_of_engagement: Optional[str] = None
    bounty_type: str
    reward_low: Optional[str] = None
    reward_medium: Optional[str] = None
    reward_high: Optional[str] = None
    reward_critical: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime
    company_name: Optional[str] = None
 
 
# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
 
class ReportCreateRequest(BaseModel):
    program_id: int
    title: str = Field(min_length=3, max_length=255)
    cwe_category: str = Field(min_length=2, max_length=150)
    severity: Literal["Low", "Medium", "High", "Critical"]
    cvss_score: float = Field(ge=0.0, le=10.0)
    impact_analysis: str = Field(min_length=5)
    poc_steps: str = Field(min_length=5)
    http_payload: Optional[str] = ""
    evidence_path: Optional[str] = None
    evidence_filename: Optional[str] = None
 
 
class ReportStatusUpdateRequest(BaseModel):
    status: Literal[
        "New", "Triaged", "Resolved", "Duplicate", "Informative", "Not Applicable"
    ]
    reputation_award: Optional[int] = None
 
 
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    program_id: int
    hacker_id: int
    title: str
    cwe_category: str
    severity: str
    cvss_score: float
    impact_analysis: str
    poc_steps: str
    http_payload: Optional[str] = None
    evidence_path: Optional[str] = None
    evidence_filename: Optional[str] = None
    status: str
    reputation_awarded: int
    created_at: datetime
    updated_at: datetime
    program_title: Optional[str] = None
    hacker_handle: Optional[str] = None
    hacker_username: Optional[str] = None
 
 
class EvidenceUploadResponse(BaseModel):
    evidence_path: str
    evidence_filename: str
 
 
# ---------------------------------------------------------------------------
# Leaderboard / Analytics
# ---------------------------------------------------------------------------
 
class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    handle: Optional[str] = None
    reputation_score: int
    resolved_reports: int
 
 
class AdminAnalytics(BaseModel):
    total_payouts_points: int
    active_programs: int
    pending_reports: int
    pending_companies: int
    pending_programs: int
    top_researchers: list[LeaderboardEntry]
 