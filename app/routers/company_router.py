"""
Company routes: create bug bounty programs, view own programs, and
triage/resolve vulnerability reports submitted against those programs.
"""
 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
 
from app.auth import require_company, require_verified, get_current_user
from app.database import get_db
from app.models import (
    Company,
    Program,
    Report,
    User,
    BountyType,
    ReportStatus,
)
from app.schemas import (
    ProgramCreateRequest,
    ProgramOut,
    ReportOut,
    ReportStatusUpdateRequest,
)
 
router = APIRouter(
    prefix="/api/company", tags=["company"], dependencies=[Depends(require_company)]
)
 
 
def _get_owned_company(current_user: User, db: Session) -> Company:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return company
 
 
@router.post(
    "/programs",
    response_model=ProgramOut,
    status_code=201,
    dependencies=[Depends(require_verified)],
)
def create_program(
    payload: ProgramCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_owned_company(current_user, db)
    if not company.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Your company must be approved by the SuperAdmin before creating programs",
        )
 
    program = Program(
        company_id=company.id,
        title=payload.title,
        target_url=payload.target_url,
        in_scope=payload.in_scope,
        out_of_scope=payload.out_of_scope,
        rules_of_engagement=payload.rules_of_engagement,
        bounty_type=BountyType(payload.bounty_type),
        reward_low=payload.reward_low,
        reward_medium=payload.reward_medium,
        reward_high=payload.reward_high,
        reward_critical=payload.reward_critical,
        is_approved=False,
        is_active=True,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
 
    item = ProgramOut.model_validate(program)
    item.company_name = company.company_name
    return item
 
 
@router.get("/my-programs", response_model=list[ProgramOut])
def my_programs(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    company = _get_owned_company(current_user, db)
    programs = db.query(Program).filter(Program.company_id == company.id).all()
    out = []
    for p in programs:
        item = ProgramOut.model_validate(p)
        item.company_name = company.company_name
        out.append(item)
    return out
 
 
@router.get("/programs/{program_id}/reports", response_model=list[ReportOut])
def program_reports(
    program_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_owned_company(current_user, db)
    program = (
        db.query(Program)
        .filter(Program.id == program_id, Program.company_id == company.id)
        .first()
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
 
    reports = (
        db.query(Report)
        .filter(Report.program_id == program_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    out = []
    for r in reports:
        item = ReportOut.model_validate(r)
        item.program_title = program.title
        if r.hacker:
            item.hacker_handle = r.hacker.handle
            item.hacker_username = r.hacker.username
        out.append(item)
    return out
 
 
@router.put("/reports/{report_id}/status", response_model=ReportOut)
def update_report_status(
    report_id: int,
    payload: ReportStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_owned_company(current_user, db)
 
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
 
    program = (
        db.query(Program)
        .filter(Program.id == report.program_id, Program.company_id == company.id)
        .first()
    )
    if not program:
        raise HTTPException(
            status_code=403, detail="This report does not belong to your programs"
        )
 
    report.status = ReportStatus(payload.status)
 
    # Award reputation points upon resolution.
    if payload.status == ReportStatus.Resolved.value:
        default_points = {
            "Low": 10,
            "Medium": 25,
            "High": 50,
            "Critical": 100,
        }
        award = (
            payload.reputation_award
            if payload.reputation_award is not None
            else default_points.get(report.severity.value, 10)
        )
        hacker = db.query(User).filter(User.id == report.hacker_id).first()
        if hacker:
            hacker.reputation_score += award
            report.reputation_awarded = award
 
    db.commit()
    db.refresh(report)
 
    item = ReportOut.model_validate(report)
    item.program_title = program.title
    if report.hacker:
        item.hacker_handle = report.hacker.handle
        item.hacker_username = report.hacker.username
    return item
 