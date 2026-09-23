"""
Hacker routes: browse approved/active bug bounty programs, submit
vulnerability reports, view own submissions, and public leaderboard.
 
The leaderboard endpoint is intentionally left open to any authenticated
user (not role-restricted) since it is meant to be a public Hall of Fame;
it is still mounted under /api/hacker for spec compliance but does not
enforce the hacker-only dependency.
"""
 
import os
import uuid
 
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
 
from app.auth import require_hacker, require_verified, get_current_user
from app.config import settings
from app.database import get_db
from app.models import Program, Report, User, UserRole, ReportStatus, Severity
from app.schemas import (
    ProgramOut,
    ReportCreateRequest,
    ReportOut,
    LeaderboardEntry,
    EvidenceUploadResponse,
)
 
router = APIRouter(prefix="/api/hacker", tags=["hacker"])
 
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
EVIDENCE_DIR = os.path.join(STATIC_DIR, "uploads", "evidence")
 
 
@router.get("/programs", response_model=list[ProgramOut])
def list_programs(db: Session = Depends(get_db)):
    """Public listing of approved + active programs. No auth required to browse."""
    programs = (
        db.query(Program)
        .filter(Program.is_approved == True, Program.is_active == True)  # noqa: E712
        .order_by(Program.created_at.desc())
        .all()
    )
    out = []
    for p in programs:
        item = ProgramOut.model_validate(p)
        if p.company:
            item.company_name = p.company.company_name
        out.append(item)
    return out
 
 
@router.get("/programs/{program_id}", response_model=ProgramOut)
def program_detail(program_id: int, db: Session = Depends(get_db)):
    program = (
        db.query(Program)
        .filter(
            Program.id == program_id,
            Program.is_approved == True,  # noqa: E712
            Program.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    item = ProgramOut.model_validate(program)
    if program.company:
        item.company_name = program.company.company_name
    return item
 
 
@router.post(
    "/reports/upload",
    response_model=EvidenceUploadResponse,
    dependencies=[Depends(require_hacker), Depends(require_verified)],
)
def upload_evidence(file: UploadFile = File(...)):
    """
    Accepts a single evidence file (screenshot, PoC recording, HAR file,
    etc.) for a vulnerability report and returns a path to attach to the
    report on submission. Used by the drag-and-drop uploader on the
    "Submit Report" form.
    """
    original_name = file.filename or "evidence"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in settings.UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"File type '{ext}' is not allowed. "
            f"Allowed types: {', '.join(settings.UPLOAD_ALLOWED_EXTENSIONS)}",
        )
 
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(EVIDENCE_DIR, stored_name)
 
    size = 0
    with open(dest_path, "wb") as out_file:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.UPLOAD_MAX_BYTES:
                out_file.close()
                os.remove(dest_path)
                raise HTTPException(
                    status_code=422,
                    detail=f"File exceeds the {settings.UPLOAD_MAX_BYTES // (1024*1024)}MB limit",
                )
            out_file.write(chunk)
 
    return EvidenceUploadResponse(
        evidence_path=f"/static/uploads/evidence/{stored_name}",
        evidence_filename=original_name,
    )
 
 
@router.post(
    "/reports",
    response_model=ReportOut,
    status_code=201,
    dependencies=[Depends(require_hacker), Depends(require_verified)],
)
def submit_report(
    payload: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = (
        db.query(Program)
        .filter(
            Program.id == payload.program_id,
            Program.is_approved == True,  # noqa: E712
            Program.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not program:
        raise HTTPException(
            status_code=404, detail="Target program not found or not active"
        )
 
    report = Report(
        program_id=program.id,
        hacker_id=current_user.id,
        title=payload.title,
        cwe_category=payload.cwe_category,
        severity=Severity(payload.severity),
        cvss_score=payload.cvss_score,
        impact_analysis=payload.impact_analysis,
        poc_steps=payload.poc_steps,
        http_payload=payload.http_payload,
        evidence_path=payload.evidence_path,
        evidence_filename=payload.evidence_filename,
        status=ReportStatus.New,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
 
    item = ReportOut.model_validate(report)
    item.program_title = program.title
    item.hacker_handle = current_user.handle
    item.hacker_username = current_user.username
    return item
 
 
@router.get(
    "/my-reports",
    response_model=list[ReportOut],
    dependencies=[Depends(require_hacker)],
)
def my_reports(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    reports = (
        db.query(Report)
        .filter(Report.hacker_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    out = []
    for r in reports:
        item = ReportOut.model_validate(r)
        if r.program:
            item.program_title = r.program.title
        item.hacker_handle = current_user.handle
        item.hacker_username = current_user.username
        out.append(item)
    return out
 
 
@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(db: Session = Depends(get_db)):
    hackers = (
        db.query(User)
        .filter(User.role == UserRole.hacker)
        .order_by(User.reputation_score.desc())
        .limit(50)
        .all()
    )
    out = []
    for i, h in enumerate(hackers, start=1):
        resolved_count = (
            db.query(Report)
            .filter(Report.hacker_id == h.id, Report.status == ReportStatus.Resolved)
            .count()
        )
        out.append(
            LeaderboardEntry(
                rank=i,
                username=h.username,
                handle=h.handle,
                reputation_score=h.reputation_score,
                resolved_reports=resolved_count,
            )
        )
    return out
 