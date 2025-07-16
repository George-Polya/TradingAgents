import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlmodel import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from member.infra.repository.member_repo import MemberRepository
from member.domain.member import Member as MemberVO
from utils.auth import Role


class TestMemberRepository:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.mock_session = Mock(spec=Session)
        self.member_repo = MemberRepository(self.mock_session)
        
        # 테스트용 데이터
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
        # Create a mock database object instead of importing the actual model
        self.test_member_db = Mock()
        for key, value in self.test_member_data.items():
            setattr(self.test_member_db, key, value)

    def test_find_by_email_success(self):
        """이메일로 멤버 조회 성공 테스트"""
        # Given
        email = "test@example.com"
        mock_query_result = Mock()
        mock_query_result.first.return_value = self.test_member_db
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            
            # When
            result = self.member_repo.find_by_email(email)
        
        # Then
        assert result is not None
        assert isinstance(result, MemberVO)
        assert result.email == email
        self.mock_session.exec.assert_called_once()

    def test_find_by_email_not_found(self):
        """이메일로 멤버 조회 - 존재하지 않음 테스트"""
        # Given
        email = "nonexistent@example.com"
        mock_query_result = Mock()
        mock_query_result.first.return_value = None
        self.mock_session.exec.return_value = mock_query_result
        
        # When
        result = self.member_repo.find_by_email(email)
        
        # Then
        assert result is None
        self.mock_session.exec.assert_called_once()

    def test_find_by_email_with_query_construction(self):
        """이메일로 멤버 조회 - 쿼리 구성 확인 테스트"""
        # Given
        email = "test@example.com"
        mock_query_result = Mock()
        mock_query_result.first.return_value = self.test_member_db
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            with patch('member.infra.repository.member_repo.select') as mock_select:
                mock_query = Mock()
                mock_query.where.return_value = mock_query
                mock_select.return_value = mock_query
                
                # When
                result = self.member_repo.find_by_email(email)
        
        # Then
        assert result is not None
        mock_select.assert_called_once()
        mock_query.where.assert_called_once()

    def test_save_success(self):
        """멤버 저장 성공 테스트"""
        # Given
        member_vo = self.test_member_vo
        mock_new_member = Mock()
        mock_new_member.id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            # When
            result = self.member_repo.save(member_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, MemberVO)
        assert result.id == mock_new_member.id
        
        # Verify Member was created with correct data
        mock_member_class.assert_called_once_with(
            id=member_vo.id,
            email=member_vo.email,
            name=member_vo.name,
            password=member_vo.password,
            role=member_vo.role,
            created_at=member_vo.created_at,
            updated_at=member_vo.updated_at
        )
        
        self.mock_session.add.assert_called_once_with(mock_new_member)
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_new_member)

    def test_save_with_none_id(self):
        """ID가 None인 멤버 저장 테스트"""
        # Given
        member_data = self.test_member_data.copy()
        member_data["id"] = None
        member_vo = MemberVO(**member_data)
        
        mock_new_member = Mock()
        mock_new_member.id = "generated_id"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            # When
            result = self.member_repo.save(member_vo)
        
        # Then
        assert result is not None
        assert result.id == mock_new_member.id
        
        # Verify Member was created with None id initially
        mock_member_class.assert_called_once_with(
            id=None,
            email=member_vo.email,
            name=member_vo.name,
            password=member_vo.password,
            role=member_vo.role,
            created_at=member_vo.created_at,
            updated_at=member_vo.updated_at
        )

    def test_save_with_different_roles(self):
        """다양한 역할을 가진 멤버 저장 테스트"""
        # Test USER role
        user_data = self.test_member_data.copy()
        user_data["role"] = Role.USER
        user_vo = MemberVO(**user_data)
        
        mock_new_member = Mock()
        mock_new_member.id = "user_id"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            result = self.member_repo.save(user_vo)
        
        assert result.role == Role.USER
        
        # Test ADMIN role
        admin_data = self.test_member_data.copy()
        admin_data["role"] = Role.ADMIN
        admin_vo = MemberVO(**admin_data)
        
        mock_new_member.id = "admin_id"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            result = self.member_repo.save(admin_vo)
        
        assert result.role == Role.ADMIN

    def test_get_members_success(self):
        """멤버 목록 조회 성공 테스트"""
        # Given
        page = 1
        items_per_page = 10
        total_count = 25
        
        # Mock count query
        mock_count_query_result = Mock()
        mock_count_query_result.one.return_value = total_count
        
        # Mock members query
        mock_members_query_result = Mock()
        mock_members_query_result.all.return_value = [self.test_member_db]
        
        self.mock_session.exec.side_effect = [mock_count_query_result, mock_members_query_result]
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            
            # When
            result_count, result_members = self.member_repo.get_members(page, items_per_page)
        
        # Then
        assert result_count == total_count
        assert len(result_members) == 1
        assert isinstance(result_members[0], MemberVO)
        assert result_members[0].id == self.test_member_data["id"]
        
        # Verify both queries were executed
        assert self.mock_session.exec.call_count == 2

    def test_get_members_empty_result(self):
        """멤버 목록 조회 - 빈 결과 테스트"""
        # Given
        page = 1
        items_per_page = 10
        total_count = 0
        
        # Mock count query
        mock_count_query_result = Mock()
        mock_count_query_result.one.return_value = total_count
        
        self.mock_session.exec.return_value = mock_count_query_result
        
        # When
        result_count, result_members = self.member_repo.get_members(page, items_per_page)
        
        # Then
        assert result_count == 0
        assert result_members == []
        
        # Verify only count query was executed
        assert self.mock_session.exec.call_count == 1

    def test_get_members_pagination(self):
        """멤버 목록 조회 - 페이지네이션 테스트"""
        # Given
        page = 3
        items_per_page = 5
        total_count = 25
        expected_offset = (page - 1) * items_per_page  # (3-1) * 5 = 10
        
        # Mock count query
        mock_count_query_result = Mock()
        mock_count_query_result.one.return_value = total_count
        
        # Mock members query
        mock_members_query_result = Mock()
        mock_members_query_result.all.return_value = [self.test_member_db]
        
        self.mock_session.exec.side_effect = [mock_count_query_result, mock_members_query_result]
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            with patch('member.infra.repository.member_repo.select') as mock_select:
                mock_query = Mock()
                mock_query.order_by.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_select.return_value = mock_query
                
                # When
                result_count, result_members = self.member_repo.get_members(page, items_per_page)
        
        # Then
        assert result_count == total_count
        assert len(result_members) == 1
        
        # Verify pagination parameters
        mock_query.offset.assert_called_once_with(expected_offset)
        mock_query.limit.assert_called_once_with(items_per_page)
        mock_query.order_by.assert_called_once()

    def test_get_members_multiple_results(self):
        """멤버 목록 조회 - 여러 결과 테스트"""
        # Given
        page = 1
        items_per_page = 10
        total_count = 3
        
        member_data_1 = self.test_member_data.copy()
        member_data_1["id"] = "member_1"
        member_data_1["email"] = "member1@example.com"
        
        member_data_2 = self.test_member_data.copy()
        member_data_2["id"] = "member_2"
        member_data_2["email"] = "member2@example.com"
        
        member_data_3 = self.test_member_data.copy()
        member_data_3["id"] = "member_3"
        member_data_3["email"] = "member3@example.com"
        
        mock_member_1 = Mock()
        for key, value in member_data_1.items():
            setattr(mock_member_1, key, value)
            
        mock_member_2 = Mock()
        for key, value in member_data_2.items():
            setattr(mock_member_2, key, value)
            
        mock_member_3 = Mock()
        for key, value in member_data_3.items():
            setattr(mock_member_3, key, value)
            
        mock_members = [mock_member_1, mock_member_2, mock_member_3]
        
        # Mock count query
        mock_count_query_result = Mock()
        mock_count_query_result.one.return_value = total_count
        
        # Mock members query
        mock_members_query_result = Mock()
        mock_members_query_result.all.return_value = mock_members
        
        self.mock_session.exec.side_effect = [mock_count_query_result, mock_members_query_result]
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.side_effect = [member_data_1, member_data_2, member_data_3]
            
            # When
            result_count, result_members = self.member_repo.get_members(page, items_per_page)
        
        # Then
        assert result_count == total_count
        assert len(result_members) == 3
        assert all(isinstance(member, MemberVO) for member in result_members)
        assert result_members[0].id == "member_1"
        assert result_members[1].id == "member_2"
        assert result_members[2].id == "member_3"

    def test_find_by_id_success(self):
        """ID로 멤버 조회 성공 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_query_result = Mock()
        mock_query_result.first.return_value = self.test_member_db
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            
            # When
            result = self.member_repo.find_by_id(member_id)
        
        # Then
        assert result is not None
        assert isinstance(result, MemberVO)
        assert result.id == member_id
        self.mock_session.exec.assert_called_once()

    def test_find_by_id_not_found(self):
        """ID로 멤버 조회 - 존재하지 않음 테스트"""
        # Given
        member_id = "non_existent_id"
        mock_query_result = Mock()
        mock_query_result.first.return_value = None
        self.mock_session.exec.return_value = mock_query_result
        
        # When
        result = self.member_repo.find_by_id(member_id)
        
        # Then
        assert result is None
        self.mock_session.exec.assert_called_once()

    def test_find_by_id_with_query_construction(self):
        """ID로 멤버 조회 - 쿼리 구성 확인 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_query_result = Mock()
        mock_query_result.first.return_value = self.test_member_db
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            with patch('member.infra.repository.member_repo.select') as mock_select:
                mock_query = Mock()
                mock_query.where.return_value = mock_query
                mock_select.return_value = mock_query
                
                # When
                result = self.member_repo.find_by_id(member_id)
        
        # Then
        assert result is not None
        mock_select.assert_called_once()
        mock_query.where.assert_called_once()

    def test_repository_initialization(self):
        """리포지토리 초기화 테스트"""
        # Given
        session = Mock(spec=Session)
        
        # When
        repo = MemberRepository(session)
        
        # Then
        assert repo.session == session
        assert isinstance(repo, MemberRepository)

    def test_save_exception_handling(self):
        """멤버 저장 예외 처리 테스트"""
        # Given
        member_vo = self.test_member_vo
        self.mock_session.add.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.member_repo.save(member_vo)

    def test_find_by_email_exception_handling(self):
        """이메일로 멤버 조회 예외 처리 테스트"""
        # Given
        email = "test@example.com"
        self.mock_session.exec.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.member_repo.find_by_email(email)

    def test_get_members_exception_handling(self):
        """멤버 목록 조회 예외 처리 테스트"""
        # Given
        page = 1
        items_per_page = 10
        self.mock_session.exec.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.member_repo.get_members(page, items_per_page)

    def test_find_by_id_exception_handling(self):
        """ID로 멤버 조회 예외 처리 테스트"""
        # Given
        member_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_session.exec.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.member_repo.find_by_id(member_id)

    def test_get_members_with_count_query(self):
        """멤버 목록 조회 - 카운트 쿼리 확인 테스트"""
        # Given
        page = 1
        items_per_page = 10
        total_count = 25
        
        # Mock count query
        mock_count_query_result = Mock()
        mock_count_query_result.one.return_value = total_count
        
        # Mock members query
        mock_members_query_result = Mock()
        mock_members_query_result.all.return_value = [self.test_member_db]
        
        self.mock_session.exec.side_effect = [mock_count_query_result, mock_members_query_result]
        
        with patch('member.infra.repository.member_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_member_data
            with patch('member.infra.repository.member_repo.select') as mock_select:
                with patch('member.infra.repository.member_repo.func') as mock_func:
                    mock_func.count.return_value = "COUNT(*)"
                    mock_select.return_value = Mock()
                    
                    # When
                    result_count, result_members = self.member_repo.get_members(page, items_per_page)
        
        # Then
        assert result_count == total_count
        mock_func.count.assert_called_once()

    def test_save_with_korean_name(self):
        """한글 이름을 가진 멤버 저장 테스트"""
        # Given
        korean_data = self.test_member_data.copy()
        korean_data["name"] = "김철수"
        member_vo = MemberVO(**korean_data)
        
        mock_new_member = Mock()
        mock_new_member.id = "korean_member_id"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            # When
            result = self.member_repo.save(member_vo)
        
        # Then
        assert result is not None
        assert result.name == "김철수"
        
        # Verify Member was created with Korean name
        mock_member_class.assert_called_once_with(
            id=member_vo.id,
            email=member_vo.email,
            name="김철수",
            password=member_vo.password,
            role=member_vo.role,
            created_at=member_vo.created_at,
            updated_at=member_vo.updated_at
        )

    def test_save_with_special_characters_in_email(self):
        """특수 문자가 포함된 이메일을 가진 멤버 저장 테스트"""
        # Given
        special_email_data = self.test_member_data.copy()
        special_email_data["email"] = "user+tag@sub-domain.example.com"
        member_vo = MemberVO(**special_email_data)
        
        mock_new_member = Mock()
        mock_new_member.id = "special_email_member_id"
        
        with patch('member.infra.repository.member_repo.Member') as mock_member_class:
            mock_member_class.return_value = mock_new_member
            
            # When
            result = self.member_repo.save(member_vo)
        
        # Then
        assert result is not None
        assert result.email == "user+tag@sub-domain.example.com"