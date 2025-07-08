import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException, status

from member.application.member_service import MemberService
from member.domain.member import Member as MemberVO
from member.domain.repository.member_repo import IMemberRepository
from utils.crypto import Crypto
from utils.auth import Role
from analysis.domain.analysis import Analysis as AnalysisVO
from sqlmodel import Session
from ulid import ULID


class TestMemberService:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        # Mock 객체들 생성
        self.mock_member_repo = Mock(spec=IMemberRepository)
        self.mock_crypto = Mock(spec=Crypto)
        self.mock_session = Mock(spec=Session)
        self.mock_ulid = Mock(spec=ULID)
        
        # MemberService 인스턴스 생성
        self.member_service = MemberService(
            member_repo=self.mock_member_repo,
            crypto=self.mock_crypto,
            session=self.mock_session,
            ulid=self.mock_ulid
        )
        
        # 테스트용 데이터
        self.test_member_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "email": "test@example.com", 
            "password": "password123",
            "role": Role.USER,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.test_member_vo = MemberVO(**self.test_member_data)

    def test_create_member_success(self):
        """회원 생성 성공 테스트"""
        # Given
        self.mock_member_repo.find_by_email.return_value = None  # 중복 이메일 없음
        self.mock_ulid.generate.return_value = self.test_member_data["id"]
        self.mock_crypto.encrypt.return_value = "encrypted_password"
        self.mock_member_repo.save.return_value = self.test_member_vo
        
        # When
        result = self.member_service.create_member(
            name="홍길동",
            email="test@example.com",
            password="password123",
            role=Role.USER
        )
        
        # Then
        assert result == self.test_member_vo
        self.mock_member_repo.find_by_email.assert_called_once_with("test@example.com")
        self.mock_crypto.encrypt.assert_called_once_with("password123")
        self.mock_member_repo.save.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_create_member_duplicate_email(self):
        """중복 이메일로 회원 생성 시 예외 발생 테스트"""
        # Given
        self.mock_member_repo.find_by_email.return_value = self.test_member_vo  # 중복 이메일 존재
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.member_service.create_member(
                name="홍길동",
                email="test@example.com",
                password="password123",
                role=Role.USER
            )
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Email already exists" in str(exc_info.value.detail)
        self.mock_session.rollback.assert_called_once()

    def test_create_member_repository_exception(self):
        """리포지토리에서 예외 발생 시 롤백 테스트"""
        # Given
        self.mock_member_repo.find_by_email.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(Exception) as exc_info:
            self.member_service.create_member(
                name="홍길동",
                email="test@example.com",
                password="password123",
                role=Role.USER
            )
        
        assert "Database error" in str(exc_info.value)
        self.mock_session.rollback.assert_called_once()

    def test_get_members_success(self):
        """회원 목록 조회 성공 테스트"""
        # Given
        expected_members = [self.test_member_vo]
        expected_total = 1
        self.mock_member_repo.get_members.return_value = (expected_total, expected_members)
        
        # When
        total, members = self.member_service.get_members(page=1, items_per_page=10)
        
        # Then
        assert total == expected_total
        assert members == expected_members
        self.mock_member_repo.get_members.assert_called_once_with(1, 10)

    def test_get_members_pagination(self):
        """페이지네이션 테스트"""
        # Given
        expected_total = 100
        expected_members = [self.test_member_vo] * 20
        self.mock_member_repo.get_members.return_value = (expected_total, expected_members)
        
        # When
        total, members = self.member_service.get_members(page=2, items_per_page=20)
        
        # Then
        assert total == expected_total
        assert len(members) == 20
        self.mock_member_repo.get_members.assert_called_once_with(2, 20)

    def test_get_member_success(self):
        """개별 회원 조회 성공 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_member_repo.find_by_id.return_value = self.test_member_vo
        
        # When
        result = self.member_service.get_member(member_id)
        
        # Then
        assert result == self.test_member_vo
        self.mock_member_repo.find_by_id.assert_called_once_with(member_id)

    def test_get_member_not_found(self):
        """존재하지 않는 회원 조회 시 404 예외 테스트"""
        # Given
        member_id = "non_existent_id"
        self.mock_member_repo.find_by_id.return_value = None
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.member_service.get_member(member_id)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Member not found" in str(exc_info.value.detail)

    @patch('member.application.member_service.create_access_token')
    def test_login_success(self, mock_create_token):
        """로그인 성공 테스트"""
        # Given
        email = "test@example.com"
        password = "password123"
        expected_token = "jwt_token_here"
        
        self.mock_member_repo.find_by_email.return_value = self.test_member_vo
        self.mock_crypto.verify.return_value = True
        mock_create_token.return_value = expected_token
        
        # When
        result = self.member_service.login(email, password)
        
        # Then
        assert result == expected_token
        self.mock_member_repo.find_by_email.assert_called_once_with(email)
        self.mock_crypto.verify.assert_called_once_with(password, self.test_member_vo.password)
        mock_create_token.assert_called_once_with(
            payload={"member_id": self.test_member_vo.id, "role": self.test_member_vo.role},
            role=self.test_member_vo.role
        )

    def test_login_invalid_email(self):
        """잘못된 이메일로 로그인 시 401 예외 테스트"""
        # Given
        email = "nonexistent@example.com"
        password = "password123"
        self.mock_member_repo.find_by_email.return_value = None
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.member_service.login(email, password)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in str(exc_info.value.detail)

    def test_login_invalid_password(self):
        """잘못된 패스워드로 로그인 시 401 예외 테스트"""
        # Given
        email = "test@example.com"
        password = "wrong_password"
        
        self.mock_member_repo.find_by_email.return_value = self.test_member_vo
        self.mock_crypto.verify.return_value = False
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.member_service.login(email, password)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in str(exc_info.value.detail)
        self.mock_crypto.verify.assert_called_once_with(password, self.test_member_vo.password)

    def test_get_analysis_sessions_by_member_success(self):
        """회원별 분석 세션 조회 성공 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        expected_analyses = [
            AnalysisVO(
                id="analysis_1",
                member_id=member_id,
                ticker="AAPL",
                analysis_date=datetime.now().date(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        self.mock_member_repo.find_analysis_sessions_by_member.return_value = expected_analyses
        
        # When
        result = self.member_service.get_analysis_sessions_by_member(member_id)
        
        # Then
        assert result == expected_analyses
        self.mock_member_repo.find_analysis_sessions_by_member.assert_called_once_with(member_id)

    def test_get_analysis_sessions_by_member_empty_result(self):
        """회원별 분석 세션이 없는 경우 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_member_repo.find_analysis_sessions_by_member.return_value = []
        
        # When
        result = self.member_service.get_analysis_sessions_by_member(member_id)
        
        # Then
        assert result == []
        self.mock_member_repo.find_analysis_sessions_by_member.assert_called_once_with(member_id)

    def test_crypto_integration(self):
        """암호화 통합 테스트"""
        # Given
        plain_password = "password123"
        encrypted_password = "encrypted_password_hash"
        
        self.mock_member_repo.find_by_email.return_value = None
        self.mock_ulid.generate.return_value = self.test_member_data["id"]
        self.mock_crypto.encrypt.return_value = encrypted_password
        
        # When
        self.member_service.create_member(
            name="홍길동",
            email="test@example.com",
            password=plain_password,
            role=Role.USER
        )
        
        # Then
        self.mock_crypto.encrypt.assert_called_once_with(plain_password)
        # save 메서드 호출 시 암호화된 패스워드가 사용되는지 확인
        call_args = self.mock_member_repo.save.call_args[0][0]
        assert call_args.password == encrypted_password

    def test_ulid_generation(self):
        """ULID 생성 테스트"""
        # Given
        expected_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_member_repo.find_by_email.return_value = None
        self.mock_ulid.generate.return_value = expected_id
        self.mock_crypto.encrypt.return_value = "encrypted_password"
        
        # When
        self.member_service.create_member(
            name="홍길동",
            email="test@example.com",
            password="password123",
            role=Role.USER
        )
        
        # Then
        self.mock_ulid.generate.assert_called_once()
        call_args = self.mock_member_repo.save.call_args[0][0]
        assert call_args.id == expected_id

    def test_datetime_handling(self):
        """datetime 처리 테스트"""
        # Given
        self.mock_member_repo.find_by_email.return_value = None
        self.mock_ulid.generate.return_value = "test_id"
        self.mock_crypto.encrypt.return_value = "encrypted_password"
        
        # When
        with patch('member.application.member_service.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            self.member_service.create_member(
                name="홍길동",
                email="test@example.com",
                password="password123",
                role=Role.USER
            )
            
            # Then
            call_args = self.mock_member_repo.save.call_args[0][0]
            assert call_args.created_at == mock_now
            assert call_args.updated_at == mock_now