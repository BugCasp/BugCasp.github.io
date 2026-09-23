"""
FastAPI application entrypoint.
 
Wires together the database, routers, CORS policy, and static SPA frontend.
On startup, creates all tables and seeds a default SuperAdmin account if
none exists yet, so the platform is immediately usable.
"""
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
 
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, UserRole
from app.auth import hash_password
from app.routers import auth_router, admin_router, company_router, hacker_router
 
# Create all tables (safe / idempotent for SQLite dev use).
Base.metadata.create_all(bind=engine)
 
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(company_router.router)
app.include_router(hacker_router.router)
 
 
@app.on_event("startup")
def seed_superadmin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.superadmin).first()
        if not existing:
            admin = User(
                username=settings.DEFAULT_SUPERADMIN_USERNAME,
                email=settings.DEFAULT_SUPERADMIN_EMAIL,
                password_hash=hash_password(settings.DEFAULT_SUPERADMIN_PASSWORD),
                role=UserRole.superadmin,
                reputation_score=0,
            )
            db.add(admin)
            db.commit()
            print(
                f"[startup] Seeded default SuperAdmin -> "
                f"username='{settings.DEFAULT_SUPERADMIN_USERNAME}' "
                f"password='{settings.DEFAULT_SUPERADMIN_PASSWORD}' "
                f"(change this immediately in production)"
            )
    finally:
        db.close()
 
 
@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
 
 
# --- Static SPA frontend ---------------------------------------------------
 
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
 
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
 
 
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
 