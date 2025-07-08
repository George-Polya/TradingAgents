import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
from fastapi import HTTPException, status, BackgroundTasks

from analysis.application.analysis_service import AnalysisService
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.domain.repository.analysis_repo import IAnalysisRepository
from analysis.interface.dto import TradingAnalysisRequest, AnalysisProgressUpdate
from analysis.infra.db_models.analysis import AnalysisStatus
from analysis.application.websocket_manager import WebSocketManager
from tradingagents.graph.trading_graph import TradingAgentsGraph
from sqlmodel import Session
from ulid import ULID


class TestAnalysisService:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        # Mock 객체들 생성
        self.mock_analysis_repo = Mock(spec=IAnalysisRepository)
        self.mock_session = Mock(spec=Session)
        self.mock_ulid = Mock(spec=ULID)
        self.mock_websocket_manager = Mock(spec=WebSocketManager)
        
        # AnalysisService 인스턴스 생성
        self.analysis_service = AnalysisService(
            analysis_repo=self.mock_analysis_repo,
            session=self.mock_session,
            ulid=self.mock_ulid,
            websocket_manager=self.mock_websocket_manager
        )
        
        # 테스트용 데이터
        self.test_analysis_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "analysis_date": "2024-01-01",
            "analysts_selected": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4",
            "status": AnalysisStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.test_analysis_vo = AnalysisVO(**self.test_analysis_data)
        
        self.test_request = TradingAnalysisRequest(
            ticker="AAPL",
            analysis_date="2024-01-01",
            analysts=["market", "news", "fundamentals"],
            research_depth=3,
            llm_provider="openai",
            backend_url="http://localhost:8000",
            shallow_thinker="gpt-3.5-turbo",
            deep_thinker="gpt-4"
        )

    def test_get_analysis_list_success(self):
        """분석 목록 조회 성공 테스트"""
        # Given
        member_id = "member_123"
        expected_analyses = [self.test_analysis_vo]
        self.mock_analysis_repo.find_by_member_id.return_value = expected_analyses
        
        # When
        result = self.analysis_service.get_analysis_list(member_id)
        
        # Then
        assert result == expected_analyses
        self.mock_analysis_repo.find_by_member_id.assert_called_once_with(member_id)

    def test_get_analysis_list_not_found(self):
        """분석 목록이 없는 경우 404 예외 테스트"""
        # Given
        member_id = "member_123"
        self.mock_analysis_repo.find_by_member_id.return_value = []
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.analysis_service.get_analysis_list(member_id)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Analysis not found" in str(exc_info.value.detail)

    def test_get_analysis_by_id_success(self):
        """ID로 분석 조회 성공 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        member_id = "member_123"
        self.mock_analysis_repo.find_by_id.return_value = self.test_analysis_vo
        
        # When
        result = self.analysis_service.get_analysis_by_id(analysis_id, member_id)
        
        # Then
        assert result == self.test_analysis_vo
        self.mock_analysis_repo.find_by_id.assert_called_once_with(analysis_id)

    def test_get_analysis_by_id_not_found(self):
        """존재하지 않는 분석 ID로 조회 시 404 예외 테스트"""
        # Given
        analysis_id = "non_existent_id"
        member_id = "member_123"
        self.mock_analysis_repo.find_by_id.return_value = None
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.analysis_service.get_analysis_by_id(analysis_id, member_id)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Analysis not found" in str(exc_info.value.detail)

    def test_get_analysis_by_id_access_denied(self):
        """다른 회원의 분석 조회 시 403 예외 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        member_id = "other_member"
        self.mock_analysis_repo.find_by_id.return_value = self.test_analysis_vo
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.analysis_service.get_analysis_by_id(analysis_id, member_id)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in str(exc_info.value.detail)

    def test_create_analysis_success(self):
        """분석 생성 성공 테스트"""
        # Given
        member_id = "member_123"
        generated_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        background_tasks = Mock(spec=BackgroundTasks)
        
        self.mock_ulid.generate.return_value = generated_id
        self.mock_analysis_repo.save.return_value = self.test_analysis_vo
        
        # When
        with patch('analysis.application.analysis_service.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            result = self.analysis_service.create_analysis(
                member_id=member_id,
                request=self.test_request,
                background_tasks=background_tasks
            )
        
        # Then
        assert result == self.test_analysis_vo
        self.mock_ulid.generate.assert_called_once()
        self.mock_analysis_repo.save.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_websocket_manager.register_analysis.assert_called_once_with(generated_id, member_id)
        background_tasks.add_task.assert_called_once()

    def test_create_analysis_save_failure(self):
        """분석 저장 실패 시 500 예외 테스트"""
        # Given
        member_id = "member_123"
        background_tasks = Mock(spec=BackgroundTasks)
        
        self.mock_ulid.generate.return_value = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_analysis_repo.save.return_value = None
        
        # When & Then
        with pytest.raises(HTTPException) as exc_info:
            self.analysis_service.create_analysis(
                member_id=member_id,
                request=self.test_request,
                background_tasks=background_tasks
            )
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to save analysis" in str(exc_info.value.detail)

    def test_create_config(self):
        """분석 설정 생성 테스트"""
        # Given
        analysis = self.test_analysis_vo
        
        # When
        with patch('analysis.application.analysis_service.DEFAULT_CONFIG', {"base_setting": "value"}):
            result = self.analysis_service._create_config(analysis)
        
        # Then
        assert result["base_setting"] == "value"
        assert result["max_debate_rounds"] == analysis.research_depth
        assert result["max_risk_discuss_rounds"] == analysis.research_depth
        assert result["quick_think_llm"] == analysis.shallow_thinker
        assert result["deep_think_llm"] == analysis.deep_thinker
        assert result["backend_url"] == analysis.backend_url
        assert result["llm_provider"] == analysis.llm_provider.lower()

    @pytest.mark.asyncio
    async def test_run_analysis_success(self):
        """분석 실행 성공 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_analysis_repo.update.return_value = self.test_analysis_vo
        
        # Mock the execute_trading_analysis method
        with patch.object(self.analysis_service, '_execute_trading_analysis', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = None
            
            # When
            await self.analysis_service._run_analysis(analysis_id)
        
        # Then
        assert self.mock_analysis_repo.update.call_count == 2  # RUNNING, COMPLETED 상태 업데이트
        assert self.mock_session.commit.call_count == 1
        self.mock_websocket_manager.send_analysis_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_analysis_failure(self):
        """분석 실행 실패 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_analysis_repo.update.return_value = self.test_analysis_vo
        
        # Mock the execute_trading_analysis method to raise an exception
        with patch.object(self.analysis_service, '_execute_trading_analysis', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Trading analysis failed")
            
            # When
            await self.analysis_service._run_analysis(analysis_id)
        
        # Then
        # 실패 시 FAILED 상태로 업데이트되는지 확인
        failed_update_call = None
        for call in self.mock_analysis_repo.update.call_args_list:
            if call[0][0].status == AnalysisStatus.FAILED:
                failed_update_call = call[0][0]
                break
        
        assert failed_update_call is not None
        assert failed_update_call.error_message == "Trading analysis failed"
        assert self.mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_process_analysis_chunk_with_updates(self):
        """분석 청크 처리 - 업데이트 데이터 있는 경우"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        chunk = {
            "market_report": "Market analysis report",
            "sentiment_report": "Sentiment analysis report",
            "news_report": "",  # 빈 값
            "fundamentals_report": None  # None 값
        }
        
        # When
        await self.analysis_service._process_analysis_chunk(analysis_id, chunk)
        
        # Then
        self.mock_analysis_repo.update.assert_called_once()
        update_vo = self.mock_analysis_repo.update.call_args[0][0]
        assert update_vo.id == analysis_id
        assert update_vo.market_report == "Market analysis report"
        assert update_vo.sentiment_report == "Sentiment analysis report"
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_analysis_chunk_no_updates(self):
        """분석 청크 처리 - 업데이트 데이터 없는 경우"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        chunk = {
            "market_report": "",
            "sentiment_report": None,
            "other_data": "some value"  # 업데이트 대상이 아닌 데이터
        }
        
        # When
        await self.analysis_service._process_analysis_chunk(analysis_id, chunk)
        
        # Then
        self.mock_analysis_repo.update.assert_not_called()
        self.mock_session.commit.assert_not_called()

    def test_generate_final_report_complete(self):
        """완전한 최종 보고서 생성 테스트"""
        # Given
        final_state = {
            "market_report": "Market analysis content",
            "sentiment_report": "Sentiment analysis content",
            "news_report": "News analysis content",
            "fundamentals_report": "Fundamentals analysis content",
            "investment_debate_state": {
                "judge_decision": "Investment decision content"
            },
            "trader_investment_plan": "Trading plan content",
            "risk_debate_state": {
                "judge_decision": "Risk management decision"
            }
        }
        
        # When
        result = self.analysis_service._generate_final_report(final_state)
        
        # Then
        assert "## Analyst Team Reports" in result
        assert "### Market Analysis" in result
        assert "### Social Sentiment" in result
        assert "### News Analysis" in result
        assert "### Fundamentals Analysis" in result
        assert "## Research Team Decision" in result
        assert "## Trading Team Plan" in result
        assert "## Portfolio Management Decision" in result
        assert "Market analysis content" in result
        assert "Investment decision content" in result

    def test_generate_final_report_empty(self):
        """빈 최종 보고서 생성 테스트"""
        # Given
        final_state = {}
        
        # When
        result = self.analysis_service._generate_final_report(final_state)
        
        # Then
        assert result == "No analysis results available."

    def test_generate_final_report_partial(self):
        """부분 최종 보고서 생성 테스트"""
        # Given
        final_state = {
            "market_report": "Market analysis content",
            "investment_debate_state": {
                "judge_decision": "Investment decision content"
            }
        }
        
        # When
        result = self.analysis_service._generate_final_report(final_state)
        
        # Then
        assert "## Analyst Team Reports" in result
        assert "### Market Analysis" in result
        assert "## Research Team Decision" in result
        assert "Market analysis content" in result
        assert "Investment decision content" in result
        # 없는 섹션들은 포함되지 않음
        assert "### Social Sentiment" not in result
        assert "## Trading Team Plan" not in result