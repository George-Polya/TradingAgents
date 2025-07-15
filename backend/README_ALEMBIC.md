# Alembic 데이터베이스 마이그레이션 가이드

## 초기 설정

### 1. 데이터베이스 초기화
```bash
# 모든 마이그레이션 적용 (테이블 생성)
alembic upgrade head
```

### 2. 현재 마이그레이션 상태 확인
```bash
alembic current
```

## 개발 워크플로우

### 1. 새로운 모델 추가 시
1. SQLModel 모델 클래스 생성
2. `backend/alembic/env.py`에 모델 import 추가
3. `backend/utils/database.py`에 모델 import 추가 (메타데이터 등록용)
4. 마이그레이션 생성:
   ```bash
   alembic revision --autogenerate -m "Add new_model table"
   ```

### 2. 기존 모델 수정 시
```bash
# 자동으로 변경사항 감지하여 마이그레이션 생성
alembic revision --autogenerate -m "Update model_name fields"
```

### 3. 마이그레이션 적용
```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade <revision>
```

### 4. 마이그레이션 롤백
```bash
# 이전 버전으로 다운그레이드
alembic downgrade -1

# 특정 버전으로 다운그레이드
alembic downgrade <revision>
```

## 중요 사항

1. **SQLModel.metadata.create_all() 사용 금지**
   - 모든 테이블 생성은 Alembic을 통해서만 수행
   - 이는 스키마 버전 관리와 일관성을 위함

2. **새 모델 추가 시 필수 작업**
   - `alembic/env.py`에 import 추가 (Alembic autogenerate용)
   - `utils/database.py`에 import 추가 (메타데이터 등록용)

3. **프로덕션 배포**
   ```bash
   # 배포 전 마이그레이션 검토
   alembic history
   
   # 프로덕션 적용
   alembic upgrade head
   ```

## 문제 해결

### 마이그레이션 충돌 시
```bash
# 현재 상태 확인
alembic current

# 히스토리 확인
alembic history

# 필요 시 특정 버전으로 강제 설정
alembic stamp <revision>
```

### 자동 생성이 변경사항을 감지하지 못할 때
1. 모든 모델이 `alembic/env.py`에 import 되었는지 확인
2. 수동으로 마이그레이션 작성:
   ```bash
   alembic revision -m "Manual migration for specific change"
   ```