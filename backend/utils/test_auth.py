import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from jose import jwt, JWTError

from utils.auth import (
    create_access_token,
    decode_access_token,
    get_current_member,
    get_admin_member,
    Role,
    CurrentMember,
    SECRET_KEY,
    ALGORITHM
)


class TestRole:
    def test_role_enum_values(self):
        """Role enum 값 테스트"""
        # Given & When & Then
        assert Role.ADMIN == "ADMIN"
        assert Role.USER == "USER"

    def test_role_enum_iteration(self):
        """Role enum 반복 테스트"""
        # Given
        roles = list(Role)
        
        # When & Then
        assert len(roles) == 2
        assert Role.ADMIN in roles
        assert Role.USER in roles


class TestCurrentMember:
    def test_current_member_creation(self):
        """CurrentMember 객체 생성 테스트"""
        # Given
        member_id = "member_123"
        role = Role.USER
        
        # When
        member = CurrentMember(id=member_id, role=role)
        
        # Then
        assert member.id == member_id
        assert member.role == role

    def test_current_member_string_representation(self):
        """CurrentMember 문자열 표현 테스트"""
        # Given
        member_id = "member_123"
        role = Role.ADMIN
        member = CurrentMember(id=member_id, role=role)
        
        # When
        result = str(member)
        
        # Then
        assert result == "member_123(ADMIN)"

    def test_current_member_with_different_roles(self):
        """다른 역할을 가진 CurrentMember 테스트"""
        # Given
        member_id = "member_456"
        
        # When
        admin_member = CurrentMember(id=member_id, role=Role.ADMIN)
        user_member = CurrentMember(id=member_id, role=Role.USER)
        
        # Then
        assert admin_member.role == Role.ADMIN
        assert user_member.role == Role.USER
        assert str(admin_member) == "member_456(ADMIN)"
        assert str(user_member) == "member_456(USER)"


class TestCreateAccessToken:
    def test_create_access_token_success(self):
        """액세스 토큰 생성 성공 테스트"""
        # Given
        payload = {"member_id": "member_123", "username": "testuser"}
        role = Role.USER
        expires_delta = timedelta(hours=1)
        
        # When
        with patch('utils.auth.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            token = create_access_token(payload, role, expires_delta)
        
        # Then
        assert token is not None
        assert isinstance(token, str)
        
        # 토큰 디코딩으로 검증 (만료 시간 검증 비활성화)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            
        assert decoded["member_id"] == "member_123"
        assert decoded["username"] == "testuser"
        assert decoded["role"] == Role.USER
        # UTC 시간으로 변환해서 비교
        import calendar
        expected_exp = calendar.timegm((mock_now + expires_delta).utctimetuple())
        assert decoded["exp"] == expected_exp

    def test_create_access_token_default_expiry(self):
        """기본 만료 시간으로 토큰 생성 테스트"""
        # Given
        payload = {"member_id": "member_123"}
        role = Role.ADMIN
        
        # When
        with patch('utils.auth.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            token = create_access_token(payload, role)
        
        # Then
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            
        # UTC 시간으로 변환해서 비교
        import calendar
        expected_exp = calendar.timegm((mock_now + timedelta(hours=6)).utctimetuple())
        assert decoded["exp"] == expected_exp

    def test_create_access_token_with_admin_role(self):
        """ADMIN 역할로 토큰 생성 테스트"""
        # Given
        payload = {"member_id": "admin_123"}
        role = Role.ADMIN
        
        # When
        token = create_access_token(payload, role)
        
        # Then
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        assert decoded["role"] == Role.ADMIN

    def test_create_access_token_payload_modification(self):
        """토큰 생성 시 payload 수정 테스트"""
        # Given
        original_payload = {"member_id": "member_123"}
        role = Role.USER
        
        # When
        create_access_token(original_payload, role)
        
        # Then
        # 원본 payload에 exp와 role이 추가되는지 확인
        assert "exp" in original_payload
        assert "role" in original_payload
        assert original_payload["role"] == Role.USER


class TestDecodeAccessToken:
    def test_decode_access_token_success(self):
        """액세스 토큰 디코딩 성공 테스트"""
        # Given
        payload = {"member_id": "member_123", "role": Role.USER}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When
        result = decode_access_token(token)
        
        # Then
        assert result["member_id"] == "member_123"
        assert result["role"] == Role.USER

    def test_decode_access_token_invalid_token(self):
        """잘못된 토큰 디코딩 테스트"""
        # Given
        invalid_token = "invalid.token.here"
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)

    def test_decode_access_token_expired_token(self):
        """만료된 토큰 디코딩 테스트"""
        # Given
        payload = {"member_id": "member_123", "exp": datetime.utcnow() - timedelta(hours=1)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)

    def test_decode_access_token_wrong_secret(self):
        """잘못된 시크릿 키로 생성된 토큰 디코딩 테스트"""
        # Given
        payload = {"member_id": "member_123"}
        token = jwt.encode(payload, "wrong_secret", algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)

    @patch('utils.auth.jwt.decode')
    def test_decode_access_token_jwt_error(self, mock_jwt_decode):
        """JWT 디코딩 에러 테스트"""
        # Given
        mock_jwt_decode.side_effect = JWTError("JWT decode error")
        token = "some.token.here"
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)


class TestGetCurrentMember:
    def test_get_current_member_success(self):
        """현재 회원 정보 조회 성공 테스트"""
        # Given
        member_id = "member_123"
        role = Role.USER
        payload = {"member_id": member_id, "role": role}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When
        result = get_current_member(token)
        
        # Then
        assert isinstance(result, CurrentMember)
        assert result.id == member_id
        assert result.role == role

    def test_get_current_member_missing_member_id(self):
        """member_id가 없는 토큰으로 조회 테스트"""
        # Given
        payload = {"role": Role.USER}  # member_id 누락
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_current_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_current_member_missing_role(self):
        """role이 없는 토큰으로 조회 테스트"""
        # Given
        payload = {"member_id": "member_123"}  # role 누락
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_current_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_current_member_invalid_token(self):
        """잘못된 토큰으로 조회 테스트"""
        # Given
        invalid_token = "invalid.token.here"
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_current_member(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_current_member_with_admin_role(self):
        """ADMIN 역할로 현재 회원 조회 테스트"""
        # Given
        member_id = "admin_123"
        role = Role.ADMIN
        payload = {"member_id": member_id, "role": role}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When
        result = get_current_member(token)
        
        # Then
        assert result.id == member_id
        assert result.role == Role.ADMIN


class TestGetAdminMember:
    def test_get_admin_member_success(self):
        """관리자 회원 정보 조회 성공 테스트"""
        # Given
        member_id = "admin_123"
        role = Role.ADMIN
        payload = {"member_id": member_id, "role": role}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When
        result = get_admin_member(token)
        
        # Then
        assert isinstance(result, CurrentMember)
        assert result.id == member_id
        assert result.role == Role.ADMIN

    def test_get_admin_member_user_role_denied(self):
        """USER 역할로 관리자 접근 시도 테스트"""
        # Given
        member_id = "user_123"
        role = Role.USER
        payload = {"member_id": member_id, "role": role}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_admin_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_admin_member_missing_role(self):
        """role이 없는 토큰으로 관리자 접근 테스트"""
        # Given
        payload = {"member_id": "admin_123"}  # role 누락
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_admin_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_admin_member_invalid_token(self):
        """잘못된 토큰으로 관리자 접근 테스트"""
        # Given
        invalid_token = "invalid.token.here"
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_admin_member(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)

    def test_get_admin_member_none_role(self):
        """role이 None인 토큰으로 관리자 접근 테스트"""
        # Given
        payload = {"member_id": "admin_123", "role": None}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            get_admin_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid token" in str(exc_info.value.detail)


class TestAuthIntegration:
    def test_token_creation_and_validation_flow(self):
        """토큰 생성부터 검증까지 통합 테스트"""
        # Given
        payload = {"member_id": "member_123", "username": "testuser"}
        role = Role.USER
        
        # When
        token = create_access_token(payload, role)
        current_member = get_current_member(token)
        
        # Then
        assert current_member.id == "member_123"
        assert current_member.role == Role.USER

    def test_admin_token_creation_and_validation_flow(self):
        """관리자 토큰 생성부터 검증까지 통합 테스트"""
        # Given
        payload = {"member_id": "admin_123", "username": "admin"}
        role = Role.ADMIN
        
        # When
        token = create_access_token(payload, role)
        admin_member = get_admin_member(token)
        
        # Then
        assert admin_member.id == "admin_123"
        assert admin_member.role == Role.ADMIN

    def test_user_cannot_access_admin_endpoint(self):
        """일반 사용자가 관리자 엔드포인트에 접근할 수 없는지 테스트"""
        # Given
        payload = {"member_id": "user_123", "username": "user"}
        role = Role.USER
        
        # When
        token = create_access_token(payload, role)
        
        # Then
        with pytest.raises(HTTPException) as exc_info:
            get_admin_member(token)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN