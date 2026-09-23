"""
Application configuration.
 
All settings are centralized here. In a real production deployment, the
SECRET_KEY and DATABASE_URL should be supplied via environment variables
rather than hard-coded, but sane local-development defaults are provided
so the platform runs immediately out of the box.
"""
 
import os
 
 
class Settings:
    # --- Security ---
    SECRET_KEY: str = os.environ.get(
        "BUGBOUNTY_SECRET_KEY",
        "dev-secret-key-change-me-in-production-1a2b3c4d5e6f7g8h9i0j",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
 
    # --- Database ---
    DATABASE_URL: str = os.environ.get(
        "BUGBOUNTY_DATABASE_URL", "sqlite:///./bugbounty.db"
    )
 
    # --- App metadata ---
    APP_NAME: str = "Bug Bounty Platform"
    APP_VERSION: str = "1.0.0"
 
    # --- CORS ---
    ALLOWED_ORIGINS: list = ["*"]
 
    # --- Seed / bootstrap ---
    # If no SuperAdmin exists at startup, one is created automatically using
    # these credentials so the platform is usable immediately.
    DEFAULT_SUPERADMIN_USERNAME: str = os.environ.get(
        "BUGBOUNTY_ADMIN_USERNAME", "admin"
    )
    DEFAULT_SUPERADMIN_EMAIL: str = os.environ.get(
        "BUGBOUNTY_ADMIN_EMAIL", "admin@bugbounty.local"
    )
    DEFAULT_SUPERADMIN_PASSWORD: str = os.environ.get(
        "BUGBOUNTY_ADMIN_PASSWORD", "AdminPass123!"
    )
 
    # --- Email verification ---
    # The base URL the frontend is served from; verification links point here.
    FRONTEND_BASE_URL: str = os.environ.get(
        "BUGBOUNTY_FRONTEND_URL", "http://localhost:8000"
    )
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 48
 
    # SMTP is optional. If SMTP_HOST is not set, verification emails are
    # simply printed to the server console instead of actually being sent,
    # so registration keeps working out of the box in local development.
    SMTP_HOST: str = os.environ.get("BUGBOUNTY_SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("BUGBOUNTY_SMTP_PORT", "587"))
    SMTP_USER: str = os.environ.get("BUGBOUNTY_SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("BUGBOUNTY_SMTP_PASSWORD", "")
    SMTP_FROM: str = os.environ.get("BUGBOUNTY_SMTP_FROM", "noreply@bugcasp.local")
 
    # --- File uploads ---
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_ALLOWED_EXTENSIONS: tuple = (
        ".png", ".jpg", ".jpeg", ".gif", ".webp",
        ".txt", ".log", ".pdf", ".zip", ".har", ".json",
    )
 
 
settings = Settings()
 