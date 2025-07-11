from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

class IRefreshTokenRepository(ABC):
    @abstractmethod
    def save(self, member_id: str, token: str, expires_at: datetime) -> None:
        pass
    
    @abstractmethod
    def find_by_token(self, token: str) -> Optional[dict]:
        pass
    
    @abstractmethod
    def revoke_token(self, token: str) -> None:
        pass
    
    @abstractmethod
    def revoke_all_member_tokens(self, member_id: str) -> None:
        pass
    
    @abstractmethod
    def is_token_valid(self, token: str) -> bool:
        pass