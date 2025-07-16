from sqlmodel import Session, select
from datetime import datetime
from typing import Optional
from refresh_token.domain.repository.refresh_token_repo import IRefreshTokenRepository
from refresh_token.infra.db_models.refresh_token import RefreshToken

class RefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, id: str, member_id: str, token: str, expires_at: datetime) -> None:
        refresh_token = RefreshToken(
            id=id,
            member_id=member_id,
            token=token,
            expires_at=expires_at
        )
        self.session.add(refresh_token)
        self.session.commit()
    
    def find_by_token(self, token: str) -> Optional[dict]:
        statement = select(RefreshToken).where(RefreshToken.token == token)
        result = self.session.exec(statement).first()
        
        if result:
            return {
                "member_id": result.member_id,
                "token": result.token,
                "expires_at": result.expires_at,
                "revoked": result.revoked
            }
        return None
    
    def revoke_token(self, token: str) -> None:
        statement = select(RefreshToken).where(RefreshToken.token == token)
        refresh_token = self.session.exec(statement).first()
        
        if refresh_token:
            refresh_token.revoked = True
            refresh_token.revoked_at = datetime.now()
            self.session.commit()
    
    def revoke_all_member_tokens(self, member_id: str) -> None:
        statement = select(RefreshToken).where(
            RefreshToken.member_id == member_id,
            RefreshToken.revoked == False
        )
        tokens = self.session.exec(statement).all()
        
        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.now()
        
        self.session.commit()
    
    def is_token_valid(self, token: str) -> bool:
        statement = select(RefreshToken).where(RefreshToken.token == token)
        refresh_token = self.session.exec(statement).first()
        
        if not refresh_token:
            return False
        
        # Check if token is not revoked and not expired
        if refresh_token.revoked:
            return False
        
        if refresh_token.expires_at < datetime.now():
            return False
        
        return True