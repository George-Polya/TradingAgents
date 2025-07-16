import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from utils.database import (
    DatabaseConnectionError,
    get_session,
    create_db_and_tables,
    check_db_connection,
    engine_config
)


class TestDatabase:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.database_url = "mysql+pymysql://user:pass@localhost/testdb"
        self.mock_settings.DEBUG = False
        self.mock_settings.is_production = False
        
        # Mock engine
        self.mock_engine = Mock()
        
        # Mock session
        self.mock_session = Mock(spec=Session)

    @patch('utils.database.get_settings')
    @patch('utils.database.create_engine')
    def test_engine_creation_success(self, mock_create_engine, mock_get_settings):
        """데이터베이스 엔진 생성 성공 테스트"""
        # Given
        mock_get_settings.return_value = self.mock_settings
        mock_create_engine.return_value = self.mock_engine
        
        # When
        with patch('utils.database.engine', self.mock_engine):
            # Import after patching to trigger engine creation
            import utils.database as db_module
        
        # Then
        mock_create_engine.assert_called_once_with(
            self.mock_settings.database_url,
            **engine_config
        )

    @patch('utils.database.get_settings')
    @patch('utils.database.create_engine')
    def test_engine_creation_failure(self, mock_create_engine, mock_get_settings):
        """데이터베이스 엔진 생성 실패 테스트"""
        # Given
        mock_get_settings.return_value = self.mock_settings
        mock_create_engine.side_effect = SQLAlchemyError("Connection failed")
        
        # When & Then
        with pytest.raises(DatabaseConnectionError):
            with patch('utils.database.logger') as mock_logger:
                # Re-import to trigger engine creation with mocked dependencies
                import importlib
                import utils.database
                importlib.reload(utils.database)

    def test_engine_config_structure(self):
        """엔진 설정 구조 테스트"""
        # Given & When
        config = engine_config
        
        # Then
        assert "pool_size" in config
        assert "max_overflow" in config
        assert "pool_pre_ping" in config
        assert "pool_recycle" in config
        assert "connect_args" in config
        
        # Test connect_args structure
        connect_args = config["connect_args"]
        assert "charset" in connect_args
        assert "connect_timeout" in connect_args
        assert "read_timeout" in connect_args
        assert "write_timeout" in connect_args
        assert "init_command" in connect_args
        
        # Test specific values
        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_pre_ping"] is True
        assert config["pool_recycle"] == 3600
        assert connect_args["charset"] == "utf8mb4"

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_get_session_success(self, mock_engine, mock_session_class):
        """세션 생성 성공 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        
        # When
        session_generator = get_session()
        session = next(session_generator)
        
        # Then
        assert session == mock_session_instance
        mock_session_class.assert_called_once_with(mock_engine)

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_get_session_commit_success(self, mock_engine, mock_session_class):
        """세션 커밋 성공 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        
        # When
        session_generator = get_session()
        session = next(session_generator)
        
        try:
            next(session_generator)  # This should trigger the finally block
        except StopIteration:
            pass
        
        # Then
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_get_session_rollback_on_exception(self, mock_engine, mock_session_class):
        """세션 예외 발생 시 롤백 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_instance.commit.side_effect = SQLAlchemyError("Commit failed")
        mock_session_class.return_value = mock_session_instance
        
        # When
        session_generator = get_session()
        session = next(session_generator)
        
        with pytest.raises(SQLAlchemyError):
            try:
                next(session_generator)  # This should trigger the exception
            except StopIteration:
                pass
        
        # Then
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()

    @patch('utils.database.get_settings')
    @patch('utils.database.SQLModel')
    @patch('utils.database.engine')
    def test_create_db_and_tables_development(self, mock_engine, mock_sqlmodel, mock_get_settings):
        """개발 환경에서 테이블 생성 테스트"""
        # Given
        mock_settings = Mock()
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        mock_metadata = Mock()
        mock_sqlmodel.metadata = mock_metadata
        
        # When
        create_db_and_tables()
        
        # Then
        mock_metadata.create_all.assert_called_once_with(mock_engine)

    @patch('utils.database.get_settings')
    @patch('utils.database.SQLModel')
    @patch('utils.database.engine')
    def test_create_db_and_tables_production(self, mock_engine, mock_sqlmodel, mock_get_settings):
        """프로덕션 환경에서 테이블 생성 건너뜀 테스트"""
        # Given
        mock_settings = Mock()
        mock_settings.is_production = True
        mock_get_settings.return_value = mock_settings
        
        mock_metadata = Mock()
        mock_sqlmodel.metadata = mock_metadata
        
        # When
        create_db_and_tables()
        
        # Then
        mock_metadata.create_all.assert_not_called()

    @patch('utils.database.get_settings')
    @patch('utils.database.SQLModel')
    @patch('utils.database.engine')
    def test_create_db_and_tables_failure(self, mock_engine, mock_sqlmodel, mock_get_settings):
        """테이블 생성 실패 테스트"""
        # Given
        mock_settings = Mock()
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        mock_metadata = Mock()
        mock_metadata.create_all.side_effect = SQLAlchemyError("Table creation failed")
        mock_sqlmodel.metadata = mock_metadata
        
        # When & Then
        with pytest.raises(DatabaseConnectionError):
            create_db_and_tables()

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_check_db_connection_success(self, mock_engine, mock_session_class):
        """데이터베이스 연결 확인 성공 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        
        # Mock context manager
        mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
        mock_session_instance.__exit__ = Mock(return_value=None)
        
        # When
        result = check_db_connection()
        
        # Then
        assert result is True
        mock_session_instance.exec.assert_called_once_with("SELECT 1")

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_check_db_connection_failure(self, mock_engine, mock_session_class):
        """데이터베이스 연결 확인 실패 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        
        # Mock context manager that raises exception
        mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
        mock_session_instance.__exit__ = Mock(return_value=None)
        mock_session_instance.exec.side_effect = OperationalError("Connection lost", None, None)
        
        # When
        result = check_db_connection()
        
        # Then
        assert result is False

    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_check_db_connection_various_exceptions(self, mock_engine, mock_session_class):
        """다양한 예외 상황에서의 연결 확인 테스트"""
        exceptions_to_test = [
            OperationalError("Connection timeout", None, None),
            SQLAlchemyError("General database error"),
            Exception("Unexpected error")
        ]
        
        for exception in exceptions_to_test:
            # Given
            mock_session_instance = Mock(spec=Session)
            mock_session_class.return_value = mock_session_instance
            mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = Mock(return_value=None)
            mock_session_instance.exec.side_effect = exception
            
            # When
            result = check_db_connection()
            
            # Then
            assert result is False, f"Should return False for exception: {type(exception).__name__}"

    def test_database_connection_error_inheritance(self):
        """DatabaseConnectionError 예외 클래스 테스트"""
        # Given
        error_message = "Database connection failed"
        
        # When
        error = DatabaseConnectionError(error_message)
        
        # Then
        assert isinstance(error, Exception)
        assert str(error) == error_message

    @patch('utils.database.get_settings')
    def test_base_dir_configuration(self, mock_get_settings):
        """BASE_DIR 설정 테스트"""
        # Given & When
        from utils.database import BASE_DIR
        
        # Then
        assert isinstance(BASE_DIR, Path)
        assert BASE_DIR.name == "backend"  # Should point to backend directory

    @patch('utils.database.Session')
    @patch('utils.database.engine')  
    def test_get_session_context_manager_behavior(self, mock_engine, mock_session_class):
        """세션 컨텍스트 매니저 동작 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        
        # When
        session_generator = get_session()
        
        # Test normal flow
        session = next(session_generator)
        assert session == mock_session_instance
        
        # Test cleanup
        try:
            next(session_generator)
        except StopIteration:
            pass
        
        # Then
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()

    @patch('utils.database.logger')
    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_get_session_logging(self, mock_engine, mock_session_class, mock_logger):
        """세션 로깅 테스트"""
        # Given
        mock_session_instance = Mock(spec=Session)
        mock_session_instance.commit.side_effect = SQLAlchemyError("Commit error")
        mock_session_class.return_value = mock_session_instance
        
        # When
        session_generator = get_session()
        session = next(session_generator)
        
        with pytest.raises(SQLAlchemyError):
            try:
                next(session_generator)
            except StopIteration:
                pass
        
        # Then
        mock_logger.error.assert_called_once()
        assert "데이터베이스 트랜잭션 실패" in mock_logger.error.call_args[0][0]

    @patch('utils.database.logger')
    @patch('utils.database.get_settings')
    @patch('utils.database.SQLModel')
    @patch('utils.database.engine')
    def test_create_db_and_tables_logging(self, mock_engine, mock_sqlmodel, mock_get_settings, mock_logger):
        """테이블 생성 로깅 테스트"""
        # Test success logging
        mock_settings = Mock()
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        mock_metadata = Mock()
        mock_sqlmodel.metadata = mock_metadata
        
        # When
        create_db_and_tables()
        
        # Then
        mock_logger.info.assert_called_with("데이터베이스 테이블 생성 완료")
        
        # Test production logging
        mock_logger.reset_mock()
        mock_settings.is_production = True
        
        create_db_and_tables()
        
        mock_logger.info.assert_called_with("프로덕션 환경 - 테이블 자동 생성 건너뜀")

    @patch('utils.database.logger')
    @patch('utils.database.Session')
    @patch('utils.database.engine')
    def test_check_db_connection_logging(self, mock_engine, mock_session_class, mock_logger):
        """연결 확인 로깅 테스트"""
        # Test success logging
        mock_session_instance = Mock(spec=Session)
        mock_session_class.return_value = mock_session_instance
        mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
        mock_session_instance.__exit__ = Mock(return_value=None)
        
        # When
        result = check_db_connection()
        
        # Then
        assert result is True
        mock_logger.info.assert_called_with("데이터베이스 연결 확인 완료")
        
        # Test failure logging
        mock_logger.reset_mock()
        mock_session_instance.exec.side_effect = OperationalError("Connection failed", None, None)
        
        result = check_db_connection()
        
        assert result is False
        mock_logger.error.assert_called_once()
        assert "데이터베이스 연결 실패" in mock_logger.error.call_args[0][0]