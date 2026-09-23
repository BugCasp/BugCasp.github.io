"""
SuperAdmin routes: approve/reject companies and programs, global report
audit view, and platform-wide analytics.
"""
 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
 
from app.auth import require_superadmin
from app.database import get_db
from app.models import Company, Program, Report, User, ReportStatus, UserRole
from app.schemas import (
    CompanyOut,
    ProgramOut,
    ReportOut,
    AdminAnalytics,
    LeaderboardEntry,
)
 
router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_superadmin)]
)
 
 
@router.get("/pending-companies", response_model=list[CompanyOut])
def pending_companies(db: Session = Depends(get_db)):
    return db.query(Company).filter(Company.is_approved == False).all()  # noqa: E712
 
 
@router.get("/all-companies", response_model=list[CompanyOut])
def all_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()
 
 
@router.post("/approve-company/{company_id}", response_model=CompanyOut)
def approve_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.is_approved = not company.is_approved
    db.commit()
    db.refresh(company)
    return company
 
 
@router.get("/pending-programs", response_model=list[ProgramOut])
def pending_programs(db: Session = Depends(get_db)):
    programs = db.query(Program).filter(Program.is_approved == False).all()  # noqa: E712
    return _enrich_programs(programs, db)
 
 
@router.get("/all-programs", response_model=list[ProgramOut])
def all_programs(db: Session = Depends(get_db)):
    programs = db.query(Program).all()
    return _enrich_programs(programs, db)
 
 
@router.post("/approve-program/{program_id}", response_model=ProgramOut)
def approve_program(program_id: int, db: Session = Depends(get_db)):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    program.is_approved = not program.is_approved
    db.commit()
    db.refresh(program)
    result = _enrich_programs([program], db)
    return result[0]
 
 
@router.get("/all-reports", response_model=list[ReportOut])
def all_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return _enrich_reports(reports, db)
 
 
@router.put("/reports/{report_id}/status", response_model=ReportOut)
def admin_update_report_status(
    report_id: int, payload: dict, db: Session = Depends(get_db)
):
    """Allows the SuperAdmin to arbitrate disputes by force-updating status."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
 
    new_status = payload.get("status")
    valid_statuses = [s.value for s in ReportStatus]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid status value")
 
    report.status = ReportStatus(new_status)
 
    reputation_award = payload.get("reputation_award")
    if new_status == ReportStatus.Resolved.value and reputation_award:
        hacker = db.query(User).filter(User.id == report.hacker_id).first()
        if hacker:
            hacker.reputation_score += int(reputation_award)
            report.reputation_awarded = int(reputation_award)
 
    db.commit()
    db.refresh(report)
    result = _enrich_reports([report], db)
    return result[0]
 
 
@router.get("/analytics", response_model=AdminAnalytics)
def analytics(db: Session = Depends(get_db)):
    total_payouts_points = (
        db.query(func.coalesce(func.sum(Report.reputation_awarded), 0)).scalar() or 0
    )
    active_programs = (
        db.query(Program)
        .filter(Program.is_approved == True, Program.is_active == True)  # noqa: E712
        .count()
    )
    pending_reports = (
        db.query(Report).filter(Report.status == ReportStatus.New).count()
    )
    pending_companies_count = (
        db.query(Company).filter(Company.is_approved == False).count()  # noqa: E712
    )
    pending_programs_count = (
        db.query(Program).filter(Program.is_approved == False).count()  # noqa: E712
    )
 
    top_hackers = (
        db.query(User)
        .filter(User.role == UserRole.hacker)
        .order_by(User.reputation_score.desc())
        .limit(5)
        .all()
    )
    top_researchers = []
    for i, h in enumerate(top_hackers, start=1):
        resolved_count = (
            db.query(Report)
            .filter(Report.hacker_id == h.id, Report.status == ReportStatus.Resolved)
            .count()
        )
        top_researchers.append(
            LeaderboardEntry(
                rank=i,
                username=h.username,
                handle=h.handle,
                reputation_score=h.reputation_score,
                resolved_reports=resolved_count,
            )
        )
 
    return AdminAnalytics(
        total_payouts_points=int(total_payouts_points),
        active_programs=active_programs,
        pending_reports=pending_reports,
        pending_companies=pending_companies_count,
        pending_programs=pending_programs_count,
        top_researchers=top_researchers,
    )
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _enrich_programs(programs, db: Session):
    out = []
    for p in programs:
        item = ProgramOut.model_validate(p)
        if p.company:
            item.company_name = p.company.company_name
        out.append(item)
    return out
 
 
def _enrich_reports(reports, db: Session):
    out = []
    for r in reports:
        item = ReportOut.model_validate(r)
        if r.program:
            item.program_title = r.program.title
        if r.hacker:
            item.hacker_handle = r.hacker.handle
            item.hacker_username = r.hacker.username
        out.append(item)
    return out
 