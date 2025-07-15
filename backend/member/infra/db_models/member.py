from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from utils.auth import Role
import uuid

# TYPE_CHECKING을 사용해서 circular import 방지
if TYPE_CHECKING:
    from analysis.infra.db_models.analysis import Analysis

class Member(SQLModel, table=True):
    __tablename__ = "members"
    id : str = Field(default=None, max_length=36, primary_key=True)
    email : str = Field(max_length=64, unique=True, nullable=False)
    name : str = Field(max_length=32, nullable=False)
    password : str = Field(max_length=64, nullable=False)
    is_active : bool = Field(default=True, nullable=False)
    created_at : datetime = Field(nullable=False)
    updated_at : datetime = Field(nullable=False)
    role : Role = Field(default=Role.USER, nullable=False)

    # Relationship 설정 - forward reference 사용
    # lazy="select" (기본값): 필요할 때마다 별도 쿼리로 로드 (N+1 문제 발생 가능)
    # lazy="selectin": IN 절을 사용하여 한 번의 추가 쿼리로 모든 관련 객체 로드
    # lazy="joined": JOIN을 사용하여 한 번의 쿼리로 로드
    # lazy="noload": 자동 로딩 비활성화, 명시적으로 로드해야 함
    analyses: list["Analysis"] = Relationship(
        back_populates="member",
        sa_relationship_kwargs={"lazy": "noload"}
    )