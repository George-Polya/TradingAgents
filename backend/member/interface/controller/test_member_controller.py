import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordRequestForm

from member.interface.controller.member_controller import router
from member.interface.dto import CreateUserBody, MemberResponse
from member.domain.member import Member as MemberVO
from utils.auth import CurrentMember, Role


class TestMemberController:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        # Test client setup
        from fastapi import FastAPI
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        # Mock current member
        self.current_member = CurrentMember(
            id="member_123",
            role=Role.USER
        )
        
        self.admin_member = CurrentMember(
            id="admin_456",
            role=Role.ADMIN
        )
        
        # Mock member service
        self.mock_member_service = Mock()
        
        # Test data
        self.test_member_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "email": "test@example.com",
            "password": "encrypted_password_hash",
            "role": Role.USER,
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        self.test_member_vo = MemberVO(**self.test_member_data)
        
        self.test_create_user_body = CreateUserBody(
            name="홍길동",
            email="test@example.com",
            password="password123",
            role=Role.USER
        )

    @patch('member.interface.controller.member_controller.Provide')
    def test_create_user_success(self, mock_provide):
        """사용자 생성 성공 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        self.mock_member_service.create_member.return_value = self.test_member_vo
        
        request_data = {
            "name": "홍길동",
            "email": "test@example.com",
            "password": "password123",
            "role": "USER"
        }
        
        # When
        with patch('member.interface.controller.member_controller.create_user') as mock_endpoint:
            mock_endpoint.return_value = MemberResponse(
                id=self.test_member_vo.id,
                name=self.test_member_vo.name,
                email=self.test_member_vo.email,
                created_at=self.test_member_vo.created_at,
                updated_at=self.test_member_vo.updated_at,
                role=self.test_member_vo.role
            )
            
            response = self.client.post("/members", json=request_data)
        
        # Then
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == self.test_member_vo.id
        assert response_data["name"] == self.test_member_vo.name
        assert response_data["email"] == self.test_member_vo.email
        assert response_data["role"] == self.test_member_vo.role.value

    @patch('member.interface.controller.member_controller.Provide')
    def test_create_user_duplicate_email(self, mock_provide):
        """사용자 생성 - 이메일 중복 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        self.mock_member_service.create_member.side_effect = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )
        
        request_data = {
            "name": "홍길동",
            "email": "existing@example.com",
            "password": "password123",
            "role": "USER"
        }
        
        # When
        with patch('member.interface.controller.member_controller.create_user') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
            
            response = self.client.post("/members", json=request_data)
        
        # Then
        assert response.status_code == 409
        assert "Email already exists" in response.json()["detail"]

    def test_create_user_validation_errors(self):
        """사용자 생성 - 검증 오류 테스트"""
        validation_test_cases = [
            {
                "name": "Empty name",
                "data": {"name": "", "email": "test@example.com", "password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Invalid email format",
                "data": {"name": "홍길동", "email": "invalid-email", "password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Empty password",
                "data": {"name": "홍길동", "email": "test@example.com", "password": ""},
                "expected_status": 422
            },
            {
                "name": "Name too long",
                "data": {"name": "a" * 50, "email": "test@example.com", "password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Email too long",
                "data": {"name": "홍길동", "email": "a" * 30 + "@example.com", "password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Password too long",
                "data": {"name": "홍길동", "email": "test@example.com", "password": "a" * 50},
                "expected_status": 422
            }
        ]
        
        for case in validation_test_cases:
            # When
            response = self.client.post("/members", json=case["data"])
            
            # Then
            assert response.status_code == case["expected_status"], f"Failed for case: {case['name']}"

    @patch('member.interface.controller.member_controller.Provide')
    def test_create_user_with_admin_role(self, mock_provide):
        """관리자 역할로 사용자 생성 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        
        admin_member_data = self.test_member_data.copy()
        admin_member_data["role"] = Role.ADMIN
        admin_member_vo = MemberVO(**admin_member_data)
        
        self.mock_member_service.create_member.return_value = admin_member_vo
        
        request_data = {
            "name": "관리자",
            "email": "admin@example.com",
            "password": "adminpass123",
            "role": "ADMIN"
        }
        
        # When
        with patch('member.interface.controller.member_controller.create_user') as mock_endpoint:
            mock_endpoint.return_value = MemberResponse(
                id=admin_member_vo.id,
                name=admin_member_vo.name,
                email=admin_member_vo.email,
                created_at=admin_member_vo.created_at,
                updated_at=admin_member_vo.updated_at,
                role=admin_member_vo.role
            )
            
            response = self.client.post("/members", json=request_data)
        
        # Then
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["role"] == Role.ADMIN.value

    @patch('member.interface.controller.member_controller.Provide')
    def test_login_success(self, mock_provide):
        """로그인 성공 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"
        self.mock_member_service.login.return_value = access_token
        
        form_data = {
            "username": "test@example.com",
            "password": "password123"
        }
        
        # When
        with patch('member.interface.controller.member_controller.login') as mock_endpoint:
            mock_endpoint.return_value = {
                "access_token": access_token,
                "token_type": "Bearer"
            }
            
            response = self.client.post("/members/login", data=form_data)
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["access_token"] == access_token
        assert response_data["token_type"] == "Bearer"

    @patch('member.interface.controller.member_controller.Provide')
    def test_login_invalid_credentials(self, mock_provide):
        """로그인 - 잘못된 자격증명 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        self.mock_member_service.login.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
        
        form_data = {
            "username": "test@example.com",
            "password": "wrongpassword"
        }
        
        # When
        with patch('member.interface.controller.member_controller.login') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
            response = self.client.post("/members/login", data=form_data)
        
        # Then
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @patch('member.interface.controller.member_controller.get_current_member')
    def test_get_current_user_info_success(self, mock_get_current_member):
        """현재 사용자 정보 조회 성공 테스트"""
        # Given
        mock_get_current_member.return_value = self.current_member
        
        # When
        with patch('member.interface.controller.member_controller.get_current_user_info') as mock_endpoint:
            mock_endpoint.return_value = {
                "user_id": self.current_member.id,
                "role": self.current_member.role,
                "message": "Successfully authenticated"
            }
            
            response = self.client.get("/members/me")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["user_id"] == self.current_member.id
        assert response_data["role"] == self.current_member.role.value
        assert "Successfully authenticated" in response_data["message"]

    @patch('member.interface.controller.member_controller.get_current_member')
    def test_get_current_user_info_unauthorized(self, mock_get_current_member):
        """현재 사용자 정보 조회 - 인증되지 않음 테스트"""
        # Given
        mock_get_current_member.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
        # When
        with patch('member.interface.controller.member_controller.get_current_user_info') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
            
            response = self.client.get("/members/me")
        
        # Then
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @patch('member.interface.controller.member_controller.get_current_member')
    @patch('member.interface.controller.member_controller.Provide')
    def test_get_member_success(self, mock_provide, mock_get_current_member):
        """멤버 조회 성공 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_member_service
        
        self.mock_member_service.get_member.return_value = self.test_member_vo
        
        # When
        with patch('member.interface.controller.member_controller.get_member') as mock_endpoint:
            mock_endpoint.return_value = MemberResponse(
                id=self.test_member_vo.id,
                name=self.test_member_vo.name,
                email=self.test_member_vo.email,
                created_at=self.test_member_vo.created_at,
                updated_at=self.test_member_vo.updated_at,
                role=self.test_member_vo.role
            )
            
            response = self.client.get(f"/members/{member_id}")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == member_id
        assert response_data["name"] == self.test_member_vo.name
        assert response_data["email"] == self.test_member_vo.email

    @patch('member.interface.controller.member_controller.get_current_member')
    @patch('member.interface.controller.member_controller.Provide')
    def test_get_member_not_found(self, mock_provide, mock_get_current_member):
        """멤버 조회 - 존재하지 않음 테스트"""
        # Given
        member_id = "non_existent_id"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_member_service
        
        self.mock_member_service.get_member.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
        
        # When
        with patch('member.interface.controller.member_controller.get_member') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
            
            response = self.client.get(f"/members/{member_id}")
        
        # Then
        assert response.status_code == 404
        assert "Member not found" in response.json()["detail"]

    def test_login_form_validation(self):
        """로그인 폼 검증 테스트"""
        validation_test_cases = [
            {
                "name": "Missing username",
                "data": {"password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Missing password",
                "data": {"username": "test@example.com"},
                "expected_status": 422
            },
            {
                "name": "Empty username",
                "data": {"username": "", "password": "password123"},
                "expected_status": 422
            },
            {
                "name": "Empty password",
                "data": {"username": "test@example.com", "password": ""},
                "expected_status": 422
            }
        ]
        
        for case in validation_test_cases:
            # When
            response = self.client.post("/members/login", data=case["data"])
            
            # Then
            assert response.status_code == case["expected_status"], f"Failed for case: {case['name']}"

    def test_create_user_with_korean_characters(self):
        """한글 문자가 포함된 사용자 생성 테스트"""
        # Given
        korean_names = [
            "김철수",
            "이영희",
            "박민수",
            "최서연",
            "한글이름테스트"
        ]
        
        with patch('member.interface.controller.member_controller.Provide') as mock_provide:
            mock_provide.__getitem__.return_value = self.mock_member_service
            
            for korean_name in korean_names:
                # Setup mock return
                korean_member_data = self.test_member_data.copy()
                korean_member_data["name"] = korean_name
                korean_member_vo = MemberVO(**korean_member_data)
                self.mock_member_service.create_member.return_value = korean_member_vo
                
                request_data = {
                    "name": korean_name,
                    "email": f"{korean_name}@example.com",
                    "password": "password123",
                    "role": "USER"
                }
                
                # When
                with patch('member.interface.controller.member_controller.create_user') as mock_endpoint:
                    mock_endpoint.return_value = MemberResponse(
                        id=korean_member_vo.id,
                        name=korean_member_vo.name,
                        email=korean_member_vo.email,
                        created_at=korean_member_vo.created_at,
                        updated_at=korean_member_vo.updated_at,
                        role=korean_member_vo.role
                    )
                    
                    response = self.client.post("/members", json=request_data)
                
                # Then
                assert response.status_code == 201, f"Failed for Korean name: {korean_name}"
                response_data = response.json()
                assert response_data["name"] == korean_name

    def test_email_format_validation(self):
        """이메일 형식 검증 테스트"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.kr",
            "admin+tag@subdomain.example.org",
            "123456@numbers.net",
            "special-chars_email@test-domain.com"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@example",
            "test@.com"
        ]
        
        # Test valid emails
        for email in valid_emails:
            request_data = {
                "name": "테스트",
                "email": email,
                "password": "password123",
                "role": "USER"
            }
            
            # Should not fail validation (might fail for other reasons)
            response = self.client.post("/members", json=request_data)
            assert response.status_code != 422, f"Valid email should pass validation: {email}"
        
        # Test invalid emails
        for email in invalid_emails:
            request_data = {
                "name": "테스트",
                "email": email,
                "password": "password123",
                "role": "USER"
            }
            
            response = self.client.post("/members", json=request_data)
            assert response.status_code == 422, f"Invalid email should fail validation: {email}"

    def test_authentication_required_endpoints(self):
        """인증이 필요한 엔드포인트 테스트"""
        authenticated_endpoints = [
            ("GET", "/members/me"),
            ("GET", "/members/test-id")
        ]
        
        for method, endpoint in authenticated_endpoints:
            # When - No authentication
            if method == "GET":
                response = self.client.get(endpoint)
            
            # Then - Should return 401 or redirect to login
            assert response.status_code in [401, 422], f"Endpoint {method} {endpoint} should require authentication"

    def test_role_based_access_scenarios(self):
        """역할 기반 접근 시나리오 테스트"""
        # Test different role combinations
        role_test_cases = [
            {
                "requesting_role": Role.USER,
                "target_member_id": "other_user_id",
                "expected_access": "allowed"  # Assuming users can view other users
            },
            {
                "requesting_role": Role.ADMIN,
                "target_member_id": "any_user_id",
                "expected_access": "allowed"  # Admins can view any user
            }
        ]
        
        for case in role_test_cases:
            current_user = CurrentMember(id="current_user", role=case["requesting_role"])
            
            with patch('member.interface.controller.member_controller.get_current_member') as mock_auth:
                with patch('member.interface.controller.member_controller.Provide') as mock_provide:
                    mock_auth.return_value = current_user
                    mock_provide.__getitem__.return_value = self.mock_member_service
                    
                    if case["expected_access"] == "allowed":
                        self.mock_member_service.get_member.return_value = self.test_member_vo
                        
                        with patch('member.interface.controller.member_controller.get_member') as mock_endpoint:
                            mock_endpoint.return_value = MemberResponse(
                                id=self.test_member_vo.id,
                                name=self.test_member_vo.name,
                                email=self.test_member_vo.email,
                                created_at=self.test_member_vo.created_at,
                                updated_at=self.test_member_vo.updated_at,
                                role=self.test_member_vo.role
                            )
                            
                            response = self.client.get(f"/members/{case['target_member_id']}")
                        
                        assert response.status_code == 200
                    else:
                        # Test forbidden access if needed
                        pass

    @patch('member.interface.controller.member_controller.Provide')
    def test_create_user_service_error(self, mock_provide):
        """사용자 생성 - 서비스 오류 테스트"""
        # Given
        mock_provide.__getitem__.return_value = self.mock_member_service
        self.mock_member_service.create_member.side_effect = Exception("Database connection failed")
        
        request_data = {
            "name": "홍길동",
            "email": "test@example.com",
            "password": "password123",
            "role": "USER"
        }
        
        # When
        with patch('member.interface.controller.member_controller.create_user') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
            
            response = self.client.post("/members", json=request_data)
        
        # Then
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]