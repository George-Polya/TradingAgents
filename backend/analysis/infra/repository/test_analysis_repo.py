import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from sqlmodel import Session
from sqlalchemy.exc import SQLAlchemyError

from analysis.infra.repository.analysis_repo import AnalysisRepository
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.infra.db_models.analysis import AnalysisStatus


class TestAnalysisRepository:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.mock_session = Mock(spec=Session)
        self.analysis_repo = AnalysisRepository(self.mock_session)
        
        # 테스트용 데이터
        self.test_analysis_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "analysis_date": date(2024, 1, 1),
            "analysts_selected": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4",
            "status": AnalysisStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "market_report": None,
            "sentiment_report": None,
            "news_report": None,
            "fundamentals_report": None,
            "investment_debate_state": None,
            "trader_investment_plan": None,
            "risk_debate_state": None,
            "final_trade_decision": None,
            "final_report": None,
            "error_message": None,
            "completed_at": None
        }
        
        self.test_analysis_vo = AnalysisVO(**self.test_analysis_data)
        # Create a mock database object instead of importing the actual model
        self.test_analysis_db = Mock()
        for key, value in self.test_analysis_data.items():
            setattr(self.test_analysis_db, key, value)

    def test_find_by_member_id_success(self):
        """멤버 ID로 분석 조회 성공 테스트"""
        # Given
        member_id = "member_123"
        mock_query_result = Mock()
        mock_query_result.all.return_value = [self.test_analysis_db]
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            
            # When
            result = self.analysis_repo.find_by_member_id(member_id)
        
        # Then
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], AnalysisVO)
        assert result[0].member_id == member_id
        self.mock_session.exec.assert_called_once()

    def test_find_by_member_id_no_results(self):
        """멤버 ID로 분석 조회 - 결과 없음 테스트"""
        # Given
        member_id = "member_123"
        mock_query_result = Mock()
        mock_query_result.all.return_value = []
        self.mock_session.exec.return_value = mock_query_result
        
        # When
        result = self.analysis_repo.find_by_member_id(member_id)
        
        # Then
        assert result is None
        self.mock_session.exec.assert_called_once()

    def test_find_by_member_id_exception(self):
        """멤버 ID로 분석 조회 - 예외 발생 테스트"""
        # Given
        member_id = "member_123"
        self.mock_session.exec.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.find_by_member_id(member_id)
        
        self.mock_session.rollback.assert_called_once()

    def test_find_by_id_success(self):
        """ID로 분석 조회 성공 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_session.get.return_value = self.test_analysis_db
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            
            # When
            result = self.analysis_repo.find_by_id(analysis_id)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        assert result.id == analysis_id
        self.mock_session.get.assert_called_once()

    def test_find_by_id_not_found(self):
        """ID로 분석 조회 - 존재하지 않음 테스트"""
        # Given
        analysis_id = "non_existent_id"
        self.mock_session.get.return_value = None
        
        # When
        result = self.analysis_repo.find_by_id(analysis_id)
        
        # Then
        assert result is None
        self.mock_session.get.assert_called_once()

    def test_find_by_id_exception(self):
        """ID로 분석 조회 - 예외 발생 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_session.get.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.find_by_id(analysis_id)
        
        self.mock_session.rollback.assert_called_once()

    def test_save_success(self):
        """분석 저장 성공 테스트"""
        # Given
        analysis_vo = self.test_analysis_vo
        mock_new_analysis = Mock()
        mock_new_analysis.id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        
        with patch('analysis.infra.repository.analysis_repo.Analysis') as mock_analysis_class:
            mock_analysis_class.return_value = mock_new_analysis
            
            # When
            result = self.analysis_repo.save(analysis_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        assert result.id == mock_new_analysis.id
        self.mock_session.add.assert_called_once_with(mock_new_analysis)
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_new_analysis)

    def test_save_exception(self):
        """분석 저장 - 예외 발생 테스트"""
        # Given
        analysis_vo = self.test_analysis_vo
        self.mock_session.add.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.save(analysis_vo)
        
        self.mock_session.rollback.assert_called_once()

    def test_update_success(self):
        """분석 업데이트 성공 테스트"""
        # Given
        analysis_vo = self.test_analysis_vo
        mock_existing_analysis = Mock()
        mock_existing_analysis.id = analysis_vo.id
        mock_existing_analysis.sqlmodel_update = Mock()
        
        self.mock_session.get.return_value = mock_existing_analysis
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            
            with patch('analysis.infra.repository.analysis_repo.datetime') as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 0, 0)
                mock_datetime.now.return_value = mock_now
                
                # When
                result = self.analysis_repo.update(analysis_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        self.mock_session.get.assert_called_once()
        mock_existing_analysis.sqlmodel_update.assert_called_once()
        self.mock_session.add.assert_called_once_with(mock_existing_analysis)
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_existing_analysis)

    def test_update_not_found(self):
        """분석 업데이트 - 존재하지 않음 테스트"""
        # Given
        analysis_vo = self.test_analysis_vo
        self.mock_session.get.return_value = None
        
        # When
        result = self.analysis_repo.update(analysis_vo)
        
        # Then
        assert result is None
        self.mock_session.get.assert_called_once()

    def test_update_exception(self):
        """분석 업데이트 - 예외 발생 테스트"""
        # Given
        analysis_vo = self.test_analysis_vo
        self.mock_session.get.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.update(analysis_vo)
        
        self.mock_session.rollback.assert_called_once()

    def test_update_with_partial_data(self):
        """분석 업데이트 - 부분 데이터 테스트"""
        # Given
        partial_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "status": AnalysisStatus.RUNNING,
            "market_report": "Updated market report"
        }
        analysis_vo = AnalysisVO(**partial_data)
        
        mock_existing_analysis = Mock()
        mock_existing_analysis.id = analysis_vo.id
        mock_existing_analysis.sqlmodel_update = Mock()
        
        self.mock_session.get.return_value = mock_existing_analysis
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            
            with patch('analysis.infra.repository.analysis_repo.datetime') as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 0, 0)
                mock_datetime.now.return_value = mock_now
                
                # When
                result = self.analysis_repo.update(analysis_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        mock_existing_analysis.sqlmodel_update.assert_called_once()
        
        # Check that exclude_unset=True was used
        update_call_args = mock_existing_analysis.sqlmodel_update.call_args[0][0]
        assert "id" in update_call_args
        assert "status" in update_call_args
        assert "market_report" in update_call_args

    def test_save_with_all_fields(self):
        """모든 필드를 포함한 분석 저장 테스트"""
        # Given
        complete_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "analysis_date": date(2024,1,1),
            "analysts_selected": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4",
            "status": AnalysisStatus.COMPLETED,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "market_report": "Complete market report",
            "sentiment_report": "Complete sentiment report",
            "news_report": "Complete news report",
            "fundamentals_report": "Complete fundamentals report",
            "investment_debate_state": {"judge_decision": "Investment debate results"},
            "trader_investment_plan": "Trading plan",
            "risk_debate_state": {"judge_decision": "Risk assessment"},
            "final_trade_decision": "BUY",
            "final_report": "Final comprehensive report",
            "error_message": None,
            "completed_at": datetime.now()
        }
        analysis_vo = AnalysisVO(**complete_data)
        
        mock_new_analysis = Mock()
        mock_new_analysis.id = complete_data["id"]
        
        with patch('analysis.infra.repository.analysis_repo.Analysis') as mock_analysis_class:
            mock_analysis_class.return_value = mock_new_analysis
            
            # When
            result = self.analysis_repo.save(analysis_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        assert result.id == complete_data["id"]
        
        # Verify Analysis was created with all data
        mock_analysis_class.assert_called_once_with(**complete_data)

    def test_update_with_error_state(self):
        """분석 업데이트 - 오류 상태 테스트"""
        # Given
        error_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "status": AnalysisStatus.FAILED,
            "error_message": "Analysis failed due to network error",
            "completed_at": datetime.now()
        }
        analysis_vo = AnalysisVO(**error_data)
        
        mock_existing_analysis = Mock()
        mock_existing_analysis.id = analysis_vo.id
        mock_existing_analysis.sqlmodel_update = Mock()
        
        self.mock_session.get.return_value = mock_existing_analysis
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            
            with patch('analysis.infra.repository.analysis_repo.datetime') as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 0, 0)
                mock_datetime.now.return_value = mock_now
                
                # When
                result = self.analysis_repo.update(analysis_vo)
        
        # Then
        assert result is not None
        assert isinstance(result, AnalysisVO)
        
        # Verify error information was passed to update
        update_call_args = mock_existing_analysis.sqlmodel_update.call_args[0][0]
        assert "status" in update_call_args
        assert "error_message" in update_call_args
        assert "completed_at" in update_call_args

    def test_find_by_member_id_multiple_analyses(self):
        """멤버 ID로 여러 분석 조회 테스트"""
        # Given
        member_id = "member_123"
        analysis_data_1 = self.test_analysis_data.copy()
        analysis_data_1["id"] = "analysis_1"
        analysis_data_2 = self.test_analysis_data.copy()
        analysis_data_2["id"] = "analysis_2"
        
        mock_analysis_1 = Mock()
        for key, value in analysis_data_1.items():
            setattr(mock_analysis_1, key, value)
            
        mock_analysis_2 = Mock()
        for key, value in analysis_data_2.items():
            setattr(mock_analysis_2, key, value)
            
        mock_analyses = [mock_analysis_1, mock_analysis_2]
        
        mock_query_result = Mock()
        mock_query_result.all.return_value = mock_analyses
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.side_effect = [analysis_data_1, analysis_data_2]
            
            # When
            result = self.analysis_repo.find_by_member_id(member_id)
        
        # Then
        assert result is not None
        assert len(result) == 2
        assert all(isinstance(analysis, AnalysisVO) for analysis in result)
        assert result[0].id == "analysis_1"
        assert result[1].id == "analysis_2"

    def test_repository_initialization(self):
        """리포지토리 초기화 테스트"""
        # Given
        session = Mock(spec=Session)
        
        # When
        repo = AnalysisRepository(session)
        
        # Then
        assert repo.session == session
        assert isinstance(repo, AnalysisRepository)

    def test_session_management_on_exception(self):
        """예외 발생 시 세션 관리 테스트"""
        # Given
        member_id = "member_123"
        
        # Test find_by_member_id exception handling
        self.mock_session.exec.side_effect = SQLAlchemyError("Database error")
        
        # When & Then
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.find_by_member_id(member_id)
        
        self.mock_session.rollback.assert_called_once()
        
        # Reset mock
        self.mock_session.reset_mock()
        
        # Test save exception handling
        self.mock_session.add.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            self.analysis_repo.save(self.test_analysis_vo)
        
        self.mock_session.rollback.assert_called_once()

    def test_find_by_member_id_ordering(self):
        """멤버 ID로 분석 조회 - 정렬 확인 테스트"""
        # Given
        member_id = "member_123"
        mock_query_result = Mock()
        mock_query_result.all.return_value = [self.test_analysis_db]
        self.mock_session.exec.return_value = mock_query_result
        
        with patch('analysis.infra.repository.analysis_repo.row_to_dict') as mock_row_to_dict:
            mock_row_to_dict.return_value = self.test_analysis_data
            with patch('analysis.infra.repository.analysis_repo.select') as mock_select:
                mock_query = Mock()
                mock_query.where.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_select.return_value = mock_query
                
                # When
                result = self.analysis_repo.find_by_member_id(member_id)
        
        # Then
        assert result is not None
        mock_query.order_by.assert_called_once()  # Verify ordering was applied