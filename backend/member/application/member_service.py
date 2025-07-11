from sqlmodel import Session
from utils.crypto import Crypto
from member.domain.repository.member_repo import IMemberRepository
from member.domain.repository.refresh_token_repo import IRefreshTokenRepository
from utils.auth import Role
from member.domain.member import Member as MemberVO
from fastapi import HTTPException, status
from datetime import datetime
from utils.auth import create_access_token, create_refresh_token
from ulid import ULID
from analysis.domain.analysis import Analysis as AnalysisVO

class MemberService:
    def __init__(
        self,
        member_repo: IMemberRepository,
        refresh_token_repo: IRefreshTokenRepository,
        crypto: Crypto,
        session: Session,
        ulid: ULID
    ):
        self.member_repo = member_repo
        self.refresh_token_repo = refresh_token_repo
        self.crypto = crypto
        self.session = session
        self.ulid = ulid

    def create_member(
        self,
        name: str,
        email: str,
        password: str,
        role: Role
    ):
        try:
            if self.member_repo.find_by_email(email):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        except Exception as e:
            self.session.rollback()
            raise e

        now = datetime.now()
        member_vo = MemberVO(
            id=self.ulid.generate(),
            name=name,
            email=email,
            password=self.crypto.encrypt(password),
            created_at=now,
            updated_at=now,
            role=role
        )

        saved_member = self.member_repo.save(member_vo)
        self.session.commit()

        return saved_member


    def get_members(
        self,
        page: int,
        items_per_page: int
    )->tuple[int, list[MemberVO]] :
        return self.member_repo.get_members(page, items_per_page)

    def get_member(
        self,
        id: str
    )->MemberVO | None:
        member = self.member_repo.find_by_id(id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member

    def login(
        self,
        email: str,
        password: str
    ):
        member = self.member_repo.find_by_email(email)
        if not member:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        if not self.crypto.verify(password, member.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Create access token
        access_token = create_access_token(
            payload={"member_id": member.id, "role": member.role},
            role=member.role,
        )
        
        # Create refresh token
        refresh_token, expires_at = create_refresh_token(
            payload={"member_id": member.id}
        )
        
        # Revoke all existing refresh tokens for this member
        self.refresh_token_repo.revoke_all_member_tokens(member.id)
        
        # Save new refresh token
        self.refresh_token_repo.save(member.id, refresh_token, expires_at)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "member": member
        }

    def get_analysis_sessions_by_member(
        self,
        member_id: str
    )->list[AnalysisVO]:
        analysis_sessions = self.member_repo.find_analysis_sessions_by_member(member_id)
        return analysis_sessions
        