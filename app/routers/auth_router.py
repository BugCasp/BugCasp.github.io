"""
Authentication routes: registration (dual flow for hackers and companies),
login, and current-user profile retrieval.
"""
 
import secrets
from datetime import datetime, timedelta
 
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
 
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.config import settings
from app.database import get_db
from app.emailer import send_verification_email
from app.models import User, UserRole, Company
from app.schemas import (
    HackerRegisterRequest,
    CompanyRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserMeResponse,
)
 
router = APIRouter(prefix="/api/auth", tags=["auth"])
 
 
def _issue_verification(user: User, db: Session) -> None:
    """Generates a fresh verification token for the user and emails it."""
    user.verification_token = secrets.token_urlsafe(32)
    user.verification_sent_at = datetime.utcnow()
    db.commit()
    send_verification_email(user.email, user.username, user.verification_token)
 
 
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: dict, db: Session = Depends(get_db)):
    """
    Registers either a Hacker or a Company depending on the `account_type`
    field in the request body ("hacker" or "company").
    """
    account_type = payload.get("account_type")
 
    if account_type == "hacker":
        try:
            data = HackerRegisterRequest(**payload)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
 
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(User).filter(User.handle == data.handle).first():
            raise HTTPException(status_code=400, detail="Handle already taken")
 
        user = User(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            role=UserRole.hacker,
            handle=data.handle,
            bio=data.bio,
            tryhackme_url=data.tryhackme_url,
            hackthebox_url=data.hackthebox_url,
            github_url=data.github_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
 
    elif account_type == "company":
        try:
            data = CompanyRegisterRequest(**payload)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
 
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
 
        user = User(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            role=UserRole.company,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
 
        company = Company(
            user_id=user.id,
            company_name=data.company_name,
            industry=data.industry,
            website_url=data.website_url,
            is_approved=False,
        )
        db.add(company)
        db.commit()
 
    else:
        raise HTTPException(
            status_code=422,
            detail="account_type must be either 'hacker' or 'company'",
        )
 
    _issue_verification(user, db)
 
    token = create_access_token(
        {"sub": user.username, "role": user.role.value, "user_id": user.id}
    )
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)
 
 
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
 
    token = create_access_token(
        {"sub": user.username, "role": user.role.value, "user_id": user.id}
    )
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)
 
 
@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link")
 
    if user.verification_sent_at and datetime.utcnow() - user.verification_sent_at > timedelta(
        hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    ):
        raise HTTPException(
            status_code=400,
            detail="This verification link has expired. Please request a new one.",
        )
 
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully"}
 
 
@router.post("/resend-verification")
def resend_verification(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.is_verified:
        return {"message": "Email already verified"}
    _issue_verification(current_user, db)
    return {"message": "Verification email sent"}
 
 
@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out = UserMeResponse.model_validate(current_user)
    if current_user.role == UserRole.company:
        company = (
            db.query(Company).filter(Company.user_id == current_user.id).first()
        )
        if company:
            out.company_is_approved = company.is_approved
            out.company_name = company.company_name
    return out
 