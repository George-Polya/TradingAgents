# Database Schema Change Process Guide

## 🚨 중요: 스키마 변경 시 반드시 따라야 할 프로세스

데이터베이스 스키마가 변경되었을 때 반드시 아래 단계를 순서대로 따라주세요. 이를 생략하면 런타임 에러가 발생합니다.

## 📋 전체 프로세스 요약

1. **모델 수정** → 2. **마이그레이션 생성** → 3. **마이그레이션 검토** → 4. **마이그레이션 적용** → 5. **검증**

## 🔄 상세 프로세스

### 1. 모델 수정
SQLModel/SQLAlchemy 모델을 수정합니다.

```python
# 예시: member/infra/db_models/member.py
class Member(SQLModel, table=True):
    # 새 필드 추가
    is_active: bool = Field(default=True, nullable=False)
    role: Role = Field(default=Role.USER, nullable=False)
```

### 2. 환경 설정 (필수!)
```bash
# .env 파일이 있는 디렉토리로 이동
cd /path/to/backend

# 환경 변수 설정
export $(cat .env | grep -v '^#' | xargs)
```

### 3. 현재 상태 확인
```bash
# 현재 적용된 마이그레이션 확인
python -m alembic current

# 마이그레이션 히스토리 확인
python -m alembic history
```

### 4. 마이그레이션 파일 생성

#### 옵션 A: 자동 생성 (권장)
```bash
# autogenerate는 현재 target_metadata가 None이므로 작동하지 않음
# env.py 수정이 필요함
```

#### 옵션 B: 수동 생성 (현재 방법)
```bash
# 새 마이그레이션 파일 생성
python -m alembic revision -m "설명적인_메시지"

# 생성된 파일을 직접 편집
```

### 5. 마이그레이션 파일 작성 예시

```python
"""add_is_active_and_role_to_members

Revision ID: c3d4e5f6g789
Revises: b9b6cdf75981
Create Date: 2025-07-16 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = 'c3d4e5f6g789'
down_revision: Union[str, None] = 'b9b6cdf75981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM 타입을 사용하는 경우
    role_enum = postgresql.ENUM('ADMIN', 'USER', name='role')
    role_enum.create(op.get_bind())
    
    # 컬럼 추가
    op.add_column('members', 
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    op.add_column('members', 
        sa.Column('role', sa.Enum('ADMIN', 'USER', name='role'), 
                  nullable=False, server_default='USER'))


def downgrade() -> None:
    # 롤백 시 수행할 작업
    op.drop_column('members', 'role')
    op.drop_column('members', 'is_active')
    
    # ENUM 타입 삭제
    role_enum = postgresql.ENUM('ADMIN', 'USER', name='role')
    role_enum.drop(op.get_bind())
```

### 6. 마이그레이션 검토
```bash
# 적용될 SQL 확인 (실제로 실행하지 않음)
python -m alembic upgrade head --sql
```

### 7. 마이그레이션 적용
```bash
# 마이그레이션 실행
python -m alembic upgrade head

# 또는 run_migration.py 사용 (환경변수 설정 필요)
export $(cat .env | grep -v '^#' | xargs) && python run_migration.py
```

### 8. 검증
```bash
# 현재 버전 확인
python -m alembic current

# 데이터베이스 직접 확인 (선택사항)
psql -U $DB_USER -d $DB_NAME -c "\d members"
```

## ⚠️ 일반적인 문제 해결

### 1. "column does not exist" 에러
**원인**: 모델에는 필드가 있지만 데이터베이스에는 해당 컬럼이 없음
**해결**: 위 프로세스를 따라 마이그레이션 생성 및 적용

### 2. "No config file 'alembic.ini' found" 에러
**원인**: alembic.ini 파일이 없거나 잘못된 위치에서 실행
**해결**: 
```bash
# backend 디렉토리에서 실행
cd /path/to/backend
python -m alembic upgrade head
```

### 3. "Database configuration not found" 에러
**원인**: 환경 변수가 설정되지 않음
**해결**:
```bash
export $(cat .env | grep -v '^#' | xargs)
```

### 4. 마이그레이션 충돌
**원인**: 여러 개발자가 동시에 마이그레이션 생성
**해결**:
```bash
# 최신 코드 pull
git pull

# 마이그레이션 다시 생성
python -m alembic revision -m "your_change"

# down_revision을 최신 버전으로 수정
```

## 📝 체크리스트

- [ ] SQLModel/SQLAlchemy 모델 수정 완료
- [ ] 환경 변수 설정 (.env 파일 로드)
- [ ] 현재 마이그레이션 상태 확인
- [ ] 마이그레이션 파일 생성
- [ ] upgrade/downgrade 함수 작성
- [ ] 마이그레이션 검토 (--sql 옵션)
- [ ] 마이그레이션 적용
- [ ] 데이터베이스 상태 검증
- [ ] 애플리케이션 테스트

## 🎯 Best Practices

1. **의미있는 마이그레이션 이름 사용**
   - Good: `add_is_active_to_members`
   - Bad: `update_table`

2. **항상 downgrade 함수 구현**
   - 롤백이 필요한 경우를 대비

3. **기본값 설정**
   - 기존 데이터가 있는 경우 NOT NULL 컬럼 추가 시 server_default 사용

4. **테스트 환경에서 먼저 실행**
   - 프로덕션 적용 전 반드시 테스트

5. **마이그레이션 파일 커밋**
   - 코드와 함께 마이그레이션 파일도 버전 관리

## 🔍 추가 명령어

```bash
# 특정 버전으로 업그레이드
python -m alembic upgrade <revision>

# 한 단계 다운그레이드
python -m alembic downgrade -1

# 특정 버전으로 다운그레이드
python -m alembic downgrade <revision>

# 마이그레이션 히스토리 상세 보기
python -m alembic history -v

# 헤드 리비전 보기
python -m alembic show head
```

## 📚 참고 자료

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- Project specific: `/backend/README_ALEMBIC.md`