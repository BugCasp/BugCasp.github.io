"""
ORM database models: User, Company, Program, Report.
 
Reputation points are stored directly on the User row (reputation_score)
and incremented whenever a Company/SuperAdmin marks a Report as "Resolved".
"""
 
import enum
from datetime import datetime
 
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    Float,
    ForeignKey,
    DateTime,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
 
from app.database import Base
 
 
class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    company = "company"
    hacker = "hacker"
 
 
class BountyType(str, enum.Enum):
    points = "points"
    cash = "cash"
 
 
class Severity(str, enum.Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"
 
 
class ReportStatus(str, enum.Enum):
    New = "New"
    Triaged = "Triaged"
    Resolved = "Resolved"
    Duplicate = "Duplicate"
    Informative = "Informative"
    NotApplicable = "Not Applicable"
 
 
class User(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, index=True)
    reputation_score = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
 
    # Email verification (sent on registration; see app/emailer.py)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), unique=True, index=True, nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
 
    # Hacker-specific profile fields (nullable, only populated for hackers)
    handle = Column(String(64), unique=True, index=True, nullable=True)
    bio = Column(Text, nullable=True)
    tryhackme_url = Column(String(500), nullable=True)
    hackthebox_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
 
    company = relationship(
        "Company", back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
    reports = relationship(
        "Report", back_populates="hacker", cascade="all, delete-orphan"
    )
 
 
class Company(Base):
    __tablename__ = "companies"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(150), nullable=False)
    website_url = Column(String(500), nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
 
    owner = relationship("User", back_populates="company")
    programs = relationship(
        "Program", back_populates="company", cascade="all, delete-orphan"
    )
 
 
class Program(Base):
    __tablename__ = "programs"
 
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    target_url = Column(String(500), nullable=False)
    in_scope = Column(Text, nullable=False)
    out_of_scope = Column(Text, nullable=False)
    rules_of_engagement = Column(Text, nullable=True)
    bounty_type = Column(SAEnum(BountyType), default=BountyType.points, nullable=False)
    reward_low = Column(String(100), nullable=True)
    reward_medium = Column(String(100), nullable=True)
    reward_high = Column(String(100), nullable=True)
    reward_critical = Column(String(100), nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
 
    company = relationship("Company", back_populates="programs")
    reports = relationship(
        "Report", back_populates="program", cascade="all, delete-orphan"
    )
 
 
class Report(Base):
    __tablename__ = "reports"
 
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    hacker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    cwe_category = Column(String(150), nullable=False)
    severity = Column(SAEnum(Severity), nullable=False)
    cvss_score = Column(Float, nullable=False)
    impact_analysis = Column(Text, nullable=False)
    poc_steps = Column(Text, nullable=False)
    http_payload = Column(Text, nullable=True)
    evidence_path = Column(String(500), nullable=True)
    evidence_filename = Column(String(255), nullable=True)
    status = Column(SAEnum(ReportStatus), default=ReportStatus.New, nullable=False)
    reputation_awarded = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
 
    program = relationship("Program", back_populates="reports")
    hacker = relationship("User", back_populates="reports")
 