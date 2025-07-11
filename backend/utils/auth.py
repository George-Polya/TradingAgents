from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends, Request, Response
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv
from enum import StrEnum
from pydantic import BaseModel
from typing import Annotated, Optional
import secrets

from config import get_settings

settings = get_settings()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15분
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7일

class Role(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"

class CurrentMember(BaseModel):
    id : str
    role : Role

    def __str__(self):
        return f"{self.id}({self.role})"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/members/login")



def create_access_token(
        payload: dict,
        role: Role,
        expires_delta: Optional[timedelta] = None
):
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    payload.update({"exp": expire, "role": role, "type": "access"})
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
        payload: dict,
        expires_delta: Optional[timedelta] = None
):
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.utcnow() + expires_delta
    # Generate unique token ID
    token_id = secrets.token_urlsafe(32)
    payload.update({"exp": expire, "type": "refresh", "jti": token_id})
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    

# ✅ 수정된 부분: Annotated 올바른 사용법
def get_current_member(token: Annotated[str, Depends(oauth2_scheme)]):
    payload = decode_access_token(token)
    member_id = payload.get("member_id")
    role = payload.get("role")
    if not member_id or not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    return CurrentMember(id=member_id, role=Role(role))

def get_admin_member(token: Annotated[str, Depends(oauth2_scheme)]):
    payload = decode_access_token(token)
    member_id = payload.get("member_id")
    role = payload.get("role")
    
    if not role or role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    return CurrentMember(id=member_id, role=Role(role))

def get_current_member_websocket(token: str) -> CurrentMember:
    """
    WebSocket용 인증 함수 - 쿼리 파라미터에서 토큰을 받아 처리
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided")
    
    payload = decode_access_token(token)
    member_id = payload.get("member_id")
    role = payload.get("role")
    if not member_id or not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    return CurrentMember(id=member_id, role=Role(role))

def get_current_member_cookie(request: Request):
    """
    쿠키에서 액세스 토큰을 읽어 현재 멤버 정보를 반환
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = decode_access_token(token)
        member_id = payload.get("member_id")
        role = payload.get("role")
        
        if not member_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return CurrentMember(id=member_id, role=Role(role))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def verify_refresh_token(token: str) -> dict:
    """
    리프레시 토큰 검증
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )