import pytest
from datetime import datetime
from pydantic import ValidationError

from member.domain.member import Member
from utils.auth import Role


class TestMember:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.valid_member_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "email": "test@example.com",
            "password": "encrypted_password_hash",
            "role": Role.USER,
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 1, 12, 0, 0)
        }

    def test_member_creation_with_all_fields(self):
        """모든 필드가 포함된 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        
        # When
        member = Member(**data)
        
        # Then
        assert member.id == data["id"]
        assert member.name == data["name"]
        assert member.email == data["email"]
        assert member.password == data["password"]
        assert member.role == data["role"]
        assert member.created_at == data["created_at"]
        assert member.updated_at == data["updated_at"]

    def test_member_creation_without_id(self):
        """ID 없이 Member 생성 테스트 (ID는 optional)"""
        # Given
        data = self.valid_member_data.copy()
        del data["id"]
        
        # When
        member = Member(**data)
        
        # Then
        assert member.id is None
        assert member.name == data["name"]
        assert member.email == data["email"]
        assert member.password == data["password"]
        assert member.role == data["role"]
        assert member.created_at == data["created_at"]
        assert member.updated_at == data["updated_at"]

    def test_member_creation_with_user_role(self):
        """USER 역할로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["role"] = Role.USER
        
        # When
        member = Member(**data)
        
        # Then
        assert member.role == Role.USER

    def test_member_creation_with_admin_role(self):
        """ADMIN 역할로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["role"] = Role.ADMIN
        
        # When
        member = Member(**data)
        
        # Then
        assert member.role == Role.ADMIN

    def test_member_creation_missing_required_fields(self):
        """필수 필드 누락 시 ValidationError 발생 테스트"""
        required_fields = ["name", "email", "password", "role", "created_at", "updated_at"]
        
        for field in required_fields:
            # Given
            data = self.valid_member_data.copy()
            del data[field]
            
            # When & Then
            with pytest.raises(ValidationError) as exc_info:
                Member(**data)
            
            assert field in str(exc_info.value)

    def test_member_creation_with_empty_name(self):
        """빈 이름으로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["name"] = ""
        
        # When
        member = Member(**data)
        
        # Then
        assert member.name == ""

    def test_member_creation_with_empty_email(self):
        """빈 이메일로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["email"] = ""
        
        # When
        member = Member(**data)
        
        # Then
        assert member.email == ""

    def test_member_creation_with_empty_password(self):
        """빈 패스워드로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["password"] = ""
        
        # When
        member = Member(**data)
        
        # Then
        assert member.password == ""

    def test_member_creation_with_korean_name(self):
        """한글 이름으로 Member 생성 테스트"""
        # Given
        korean_names = ["김철수", "이영희", "박민수", "최서연"]
        
        for name in korean_names:
            data = self.valid_member_data.copy()
            data["name"] = name
            
            # When
            member = Member(**data)
            
            # Then
            assert member.name == name

    def test_member_creation_with_english_name(self):
        """영문 이름으로 Member 생성 테스트"""
        # Given
        english_names = ["John Doe", "Jane Smith", "Michael Johnson", "Sarah Wilson"]
        
        for name in english_names:
            data = self.valid_member_data.copy()
            data["name"] = name
            
            # When
            member = Member(**data)
            
            # Then
            assert member.name == name

    def test_member_creation_with_various_email_formats(self):
        """다양한 이메일 형식으로 Member 생성 테스트"""
        # Given
        email_formats = [
            "test@example.com",
            "user.name@domain.co.kr",
            "admin+tag@subdomain.example.org",
            "123456@numbers.net",
            "special-chars_email@test-domain.com"
        ]
        
        for email in email_formats:
            data = self.valid_member_data.copy()
            data["email"] = email
            
            # When
            member = Member(**data)
            
            # Then
            assert member.email == email

    def test_member_creation_with_long_password(self):
        """긴 패스워드로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        long_password = "a" * 100  # 100자 길이
        data["password"] = long_password
        
        # When
        member = Member(**data)
        
        # Then
        assert member.password == long_password
        assert len(member.password) == 100

    def test_member_creation_with_special_characters_in_password(self):
        """특수 문자가 포함된 패스워드로 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        special_password = "P@ssw0rd!@#$%^&*()"
        data["password"] = special_password
        
        # When
        member = Member(**data)
        
        # Then
        assert member.password == special_password

    def test_member_creation_with_different_timestamps(self):
        """다양한 타임스탬프로 Member 생성 테스트"""
        # Given
        timestamps = [
            datetime(2023, 1, 1, 0, 0, 0),
            datetime(2024, 6, 15, 14, 30, 45),
            datetime(2024, 12, 31, 23, 59, 59),
            datetime.now()
        ]
        
        for timestamp in timestamps:
            data = self.valid_member_data.copy()
            data["created_at"] = timestamp
            data["updated_at"] = timestamp
            
            # When
            member = Member(**data)
            
            # Then
            assert member.created_at == timestamp
            assert member.updated_at == timestamp

    def test_member_creation_with_different_created_and_updated_times(self):
        """생성 시간과 수정 시간이 다른 Member 생성 테스트"""
        # Given
        data = self.valid_member_data.copy()
        created_time = datetime(2024, 1, 1, 12, 0, 0)
        updated_time = datetime(2024, 1, 2, 15, 30, 0)
        data["created_at"] = created_time
        data["updated_at"] = updated_time
        
        # When
        member = Member(**data)
        
        # Then
        assert member.created_at == created_time
        assert member.updated_at == updated_time
        assert member.updated_at > member.created_at

    def test_member_creation_with_invalid_role_string(self):
        """잘못된 역할 문자열로 Member 생성 시 ValidationError 테스트"""
        # Given
        data = self.valid_member_data.copy()
        data["role"] = "INVALID_ROLE"
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            Member(**data)
        
        assert "role" in str(exc_info.value).lower()

    def test_member_creation_with_none_values(self):
        """None 값으로 필수 필드 설정 시 ValidationError 테스트"""
        required_fields = ["name", "email", "password", "role", "created_at", "updated_at"]
        
        for field in required_fields:
            # Given
            data = self.valid_member_data.copy()
            data[field] = None
            
            # When & Then
            with pytest.raises(ValidationError) as exc_info:
                Member(**data)
            
            assert field in str(exc_info.value)

    def test_member_model_immutability(self):
        """Member 모델의 가변성 테스트 (Pydantic BaseModel은 기본적으로 가변)"""
        # Given
        data = self.valid_member_data.copy()
        member = Member(**data)
        original_name = member.name
        
        # When
        member.name = "새로운 이름"
        
        # Then
        assert member.name == "새로운 이름"
        assert member.name != original_name

    def test_member_model_dict_conversion(self):
        """Member 모델의 딕셔너리 변환 테스트"""
        # Given
        data = self.valid_member_data.copy()
        member = Member(**data)
        
        # When
        member_dict = member.model_dump()
        
        # Then
        assert isinstance(member_dict, dict)
        for key, value in data.items():
            assert member_dict[key] == value

    def test_member_model_json_serialization(self):
        """Member 모델의 JSON 직렬화 테스트"""
        # Given
        data = self.valid_member_data.copy()
        member = Member(**data)
        
        # When
        json_str = member.model_dump_json()
        
        # Then
        assert isinstance(json_str, str)
        assert data["id"] in json_str
        assert data["name"] in json_str
        assert data["email"] in json_str

    def test_member_model_validation(self):
        """Member 모델 검증 테스트"""
        # Given
        data = self.valid_member_data.copy()
        
        # When
        member = Member(**data)
        
        # Then
        # 모델이 정상적으로 검증되고 생성됨
        assert isinstance(member, Member)
        
        # 모든 필드가 올바르게 설정됨
        for key, value in data.items():
            assert getattr(member, key) == value

    def test_member_equality(self):
        """같은 데이터로 생성된 Member 객체 비교 테스트"""
        # Given
        data = self.valid_member_data.copy()
        
        # When
        member1 = Member(**data)
        member2 = Member(**data)
        
        # Then
        assert member1.model_dump() == member2.model_dump()

    def test_member_with_ulid_format_id(self):
        """ULID 형식의 ID로 Member 생성 테스트"""
        # Given
        ulid_examples = [
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "01BX5ZZKBKACTAV9WEVGEMMVS0",
            "01BJQE4QTHMFP0YHVMFABMX8DN"
        ]
        
        for ulid in ulid_examples:
            data = self.valid_member_data.copy()
            data["id"] = ulid
            
            # When
            member = Member(**data)
            
            # Then
            assert member.id == ulid
            assert len(member.id) == 26  # ULID는 26자리

    def test_member_role_enum_functionality(self):
        """Role enum 기능 테스트"""
        # Given
        data_user = self.valid_member_data.copy()
        data_admin = self.valid_member_data.copy()
        
        data_user["role"] = Role.USER
        data_admin["role"] = Role.ADMIN
        
        # When
        user_member = Member(**data_user)
        admin_member = Member(**data_admin)
        
        # Then
        assert user_member.role == Role.USER
        assert admin_member.role == Role.ADMIN
        assert user_member.role != admin_member.role
        assert str(user_member.role) == "USER"
        assert str(admin_member.role) == "ADMIN"