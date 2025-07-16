from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"
    
    id: Optional[str] = Field(default=None, primary_key=True)
    member_id: str = Field(foreign_key="member.id", index=True, nullable=False)
    token: str = Field(unique=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)
    revoked: bool = Field(default=False)
    revoked_at: Optional[datetime] = Field(default=None)