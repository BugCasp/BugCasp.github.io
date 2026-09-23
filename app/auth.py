"""
Authentication utilities: password hashing, JWT creation/verification,
and FastAPI dependencies for enforcing role-based access control.
"""
 
from datetime import datetime, timedelta
from typing import Optional
 
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
 
from app.config import settings
from app.database import get_db
from app.models import User, UserRole
 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
 
 
# ---------------------------------------------------------------------------
# Password hashing
#
# We call bcrypt directly rather than going through passlib: passlib is
# unmaintained and its bcrypt backend detection breaks on modern bcrypt
# releases (>=4.1), which no longer expose the internal attribute passlib
# probes for. bcrypt itself also has a hard 72-byte input limit, so inputs
# are truncated to that length before hashing/verifying (as bcrypt's own
# docs recommend).
# ---------------------------------------------------------------------------
 
_BCRYPT_MAX_BYTES = 72
 
 
def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")
 
 
def verify_password(plain_password: str, password_hash: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pwd_bytes, password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/foreign hash format.
        return False
 
 
# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
 
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
 
 
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
 
# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
 
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
 
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
 
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
 
 
def require_role(*allowed_roles: UserRole):
    """Returns a FastAPI dependency that only allows the given role(s)."""
 
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user
 
    return role_checker
 
 
require_superadmin = require_role(UserRole.superadmin)
require_company = require_role(UserRole.company)
require_hacker = require_role(UserRole.hacker)
require_company_or_admin = require_role(UserRole.company, UserRole.superadmin)
 
 
def require_verified(current_user: User = Depends(get_current_user)) -> User:
    return current_user
 