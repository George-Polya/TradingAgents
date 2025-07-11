from fastapi import APIRouter, status, Depends, HTTPException, Response, Request
from member.interface.dto import CreateUserBody, MemberResponse
from member.application.member_service import MemberService
from typing import Annotated
from utils.containers import Container
from dependency_injector.wiring import inject, Provide
from fastapi.security import OAuth2PasswordRequestForm
from utils.auth import get_current_member, CurrentMember, get_admin_member, verify_refresh_token, create_access_token
from analysis.interface.dto import AnalysisSessionResponse
from analysis.application.analysis_service import AnalysisService
from pydantic import BaseModel

router = APIRouter(prefix="/members", tags=["members"])

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    member: MemberResponse

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("", status_code=status.HTTP_201_CREATED, response_model=MemberResponse)
@inject
async def create_user(
    member: CreateUserBody,
    member_service: MemberService = Depends(Provide[Container.member_service])
):
    created_member = member_service.create_member(
        member.name,
        member.email,
        member.password,
        member.role
    )

    return created_member

@router.post("/login", response_model=LoginResponse)
@inject
def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    member_service: MemberService = Depends(Provide[Container.member_service])
):
    login_result = member_service.login(
        email=form_data.username,
        password=form_data.password
    )
    
    # Set refresh token as HttpOnly cookie for security
    response.set_cookie(
        key="refresh_token",
        value=login_result["refresh_token"],
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=60 * 60 * 24 * 7  # 7 days
    )
    
    return LoginResponse(
        access_token=login_result["access_token"],
        refresh_token=login_result["refresh_token"],
        token_type="bearer",
        member=MemberResponse(
            id=login_result["member"].id,
            name=login_result["member"].name,
            email=login_result["member"].email,
            role=login_result["member"].role,
            created_at=login_result["member"].created_at,
            updated_at=login_result["member"].updated_at
        )
    )

@router.get("/me", response_model=MemberResponse)
@inject
def get_current_user_info(
    current_user: CurrentMember = Depends(get_current_member),
    member_service: MemberService = Depends(Provide[Container.member_service])
):
    """
    현재 로그인한 사용자 정보를 조회합니다.
    이 엔드포인트는 JWT 토큰이 필요하며, Swagger UI에서 Authorize 버튼을 활성화합니다.
    """
    member = member_service.get_member(current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return member

@router.post("/refresh", response_model=RefreshResponse)
@inject
def refresh_token(
    request: Request,
    member_service: MemberService = Depends(Provide[Container.member_service])
):
    """
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급합니다.
    쿠키에서 refresh token을 읽어 처리합니다.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    # Verify refresh token
    try:
        payload = verify_refresh_token(refresh_token)
        member_id = payload.get("member_id")
        
        # Check if token is valid in database
        if not member_service.refresh_token_repo.is_token_valid(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get member info
        member = member_service.get_member(member_id)
        
        # Create new access token
        access_token = create_access_token(
            payload={"member_id": member.id, "role": member.role},
            role=member.role
        )
        
        return RefreshResponse(
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout")
@inject
def logout(
    request: Request,
    response: Response,
    current_member: CurrentMember = Depends(get_current_member),
    member_service: MemberService = Depends(Provide[Container.member_service])
):
    """
    로그아웃 - 리프레시 토큰을 무효화하고 쿠키를 삭제합니다.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    # Revoke refresh token in database
    if refresh_token:
        member_service.refresh_token_repo.revoke_token(refresh_token)
    
    # Delete refresh token cookie
    response.delete_cookie("refresh_token")
    
    return {"message": "Logout successful"}

