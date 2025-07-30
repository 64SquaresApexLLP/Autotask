"""Authentication and authorization utilities."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, TechnicianDummyData

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def authenticate_technician(db: Session, username: str, password: str) -> Optional[TechnicianDummyData]:
    """Authenticate technician credentials."""
    try:
        # Try to find by email first, then by technician_id
        technician = db.query(TechnicianDummyData).filter(
            (TechnicianDummyData.email == username) |
            (TechnicianDummyData.technician_id == username)
        ).first()

        if not technician:
            return None

        # For demo purposes, check plain text password
        # In production, use proper password hashing
        if technician.technician_password != password:
            return None

        return technician

    except Exception as e:
        logger.error(f"Database error during authentication: {e}")
        # Re-raise the exception to be handled by the calling function
        raise


async def get_current_technician(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TechnicianDummyData:
    """Get current authenticated technician."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # The username in JWT is the email, so search by email first
    technician = db.query(TechnicianDummyData).filter(
        TechnicianDummyData.email == username
    ).first()

    # If not found by email, try by technician_id
    if not technician:
        technician = db.query(TechnicianDummyData).filter(
            TechnicianDummyData.technician_id == username
        ).first()

    if technician is None:
        raise credentials_exception

    if not technician.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return technician


def require_role(required_role: str):
    """Decorator to require specific role."""
    def role_checker(current_technician: TechnicianDummyData = Depends(get_current_technician)):
        if current_technician.role != required_role and current_technician.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_technician
    return role_checker


# Dependency for admin-only endpoints
get_admin_technician = require_role("admin")
