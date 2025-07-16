import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
from fastapi import HTTPException, status, BackgroundTasks, WebSocket
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from analysis.interface.controller.analysis_controller import router
from analysis.interface.dto import (
    TradingAnalysisRequest, 
    AnalysisSessionResponse, 
    AnalysisResultResponse,
    AnalystType
)
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.infra.db_models.analysis import AnalysisStatus
from utils.auth import CurrentMember, Role


class TestAnalysisController:
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
        
        # Mock analysis service
        self.mock_analysis_service = Mock()
        
        # Mock websocket manager
        self.mock_websocket_manager = Mock()
        
        # Test data
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
        
        self.test_request = TradingAnalysisRequest(
            ticker="AAPL",
            analysis_date="2024-01-01",
            analysts=[AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
            research_depth=3,
            llm_provider="openai",
            backend_url="http://localhost:8000",
            shallow_thinker="gpt-3.5-turbo",
            deep_thinker="gpt-4"
        )

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_list_for_member_success(self, mock_provide, mock_get_current_member):
        """분석 목록 조회 성공 테스트"""
        # Given
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        expected_analyses = [self.test_analysis_vo]
        self.mock_analysis_service.get_analysis_list.return_value = expected_analyses
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_list_for_member') as mock_endpoint:
            mock_endpoint.return_value = [
                AnalysisSessionResponse(
                    id=self.test_analysis_vo.id,
                    ticker=self.test_analysis_vo.ticker,
                    status=self.test_analysis_vo.status,
                    shallow_thinker=self.test_analysis_vo.shallow_thinker,
                    deep_thinker=self.test_analysis_vo.deep_thinker
                )
            ]
            
            response = self.client.get("/analysis/")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["id"] == self.test_analysis_vo.id 
        assert response_data[0]["ticker"] == self.test_analysis_vo.ticker

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_list_for_member_not_found(self, mock_provide, mock_get_current_member):
        """분석 목록 조회 - 데이터 없음 테스트"""
        # Given
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        self.mock_analysis_service.get_analysis_list.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_list_for_member') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
            
            response = self.client.get("/analysis/")
        
        # Then
        assert response.status_code == 404
        assert "Analysis not found" in response.json()["detail"]

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_start_analysis_session_success(self, mock_provide, mock_get_current_member):
        """분석 세션 시작 성공 테스트"""
        # Given
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        self.mock_analysis_service.create_analysis.return_value = self.test_analysis_vo
        
        request_data = {
            "ticker": "AAPL",
            "analysis_date": "2024-01-01",
            "analysts": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4"
        }
        
        # When
        with patch('analysis.interface.controller.analysis_controller.start_analysis_session') as mock_endpoint:
            mock_endpoint.return_value = AnalysisSessionResponse(
                **self.test_analysis_vo.model_dump()
            )
            
            response = self.client.post("/analysis/start", json=request_data)
        
        # Then
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["id"] == self.test_analysis_vo.id
        assert response_data["ticker"] == self.test_analysis_vo.ticker
        assert response_data["status"] == self.test_analysis_vo.status.value

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_start_analysis_session_failure(self, mock_provide, mock_get_current_member):
        """분석 세션 시작 실패 테스트"""
        # Given
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        self.mock_analysis_service.create_analysis.side_effect = Exception("Service unavailable")
        
        request_data = {
            "ticker": "AAPL",
            "analysis_date": "2024-01-01",
            "analysts": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4"
        }
        
        # When
        with patch('analysis.interface.controller.analysis_controller.start_analysis_session') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start analysis: Service unavailable"
            )
            
            response = self.client.post("/analysis/start", json=request_data)
        
        # Then
        assert response.status_code == 500
        assert "Failed to start analysis" in response.json()["detail"]

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_result_success(self, mock_provide, mock_get_current_member):
        """분석 결과 조회 성공 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        completed_analysis_data = self.test_analysis_data.copy()
        completed_analysis_data.update({
            "status": AnalysisStatus.COMPLETED,
            "market_report": "Market analysis complete",
            "final_report": "Final report complete",
            "completed_at": datetime.now()
        })
        completed_analysis = AnalysisVO(**completed_analysis_data)
        
        self.mock_analysis_service.get_analysis_by_id.return_value = completed_analysis
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_result') as mock_endpoint:
            mock_endpoint.return_value = AnalysisResultResponse(
                id=completed_analysis.id,
                ticker=completed_analysis.ticker,
                analysis_date=completed_analysis.analysis_date.isoformat(),
                status=completed_analysis.status,
                market_report=completed_analysis.market_report,
                news_report=completed_analysis.news_report,
                fundamentals_report=completed_analysis.fundamentals_report,
                investment_debate_state=completed_analysis.investment_debate_state,
                trader_investment_plan=completed_analysis.trader_investment_plan,
                risk_debate_state=completed_analysis.risk_debate_state,
                final_trade_decision=completed_analysis.final_trade_decision,
                final_report=completed_analysis.final_report,
                created_at=completed_analysis.created_at.isoformat(),
                completed_at=completed_analysis.completed_at.isoformat() if completed_analysis.completed_at else None,
                error_message=completed_analysis.error_message
            )
            
            response = self.client.get(f"/analysis/{analysis_id}")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == analysis_id
        assert response_data["status"] == AnalysisStatus.COMPLETED.value
        assert response_data["market_report"] == "Market analysis complete"

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_result_not_found(self, mock_provide, mock_get_current_member):
        """분석 결과 조회 - 존재하지 않음 테스트"""
        # Given
        analysis_id = "non_existent_id"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        self.mock_analysis_service.get_analysis_by_id.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_result') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
            
            response = self.client.get(f"/analysis/{analysis_id}")
        
        # Then
        assert response.status_code == 404
        assert "Analysis not found" in response.json()["detail"]

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_result_access_denied(self, mock_provide, mock_get_current_member):
        """분석 결과 조회 - 접근 거부 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        self.mock_analysis_service.get_analysis_by_id.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_result') as mock_endpoint:
            mock_endpoint.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
            response = self.client.get(f"/analysis/{analysis_id}")
        
        # Then
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @patch('analysis.interface.controller.analysis_controller.get_current_member')
    @patch('analysis.interface.controller.analysis_controller.Provide')
    def test_get_analysis_status_success(self, mock_provide, mock_get_current_member):
        """분석 상태 조회 성공 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_get_current_member.return_value = self.current_member
        mock_provide.__getitem__.return_value = self.mock_analysis_service
        
        running_analysis_data = self.test_analysis_data.copy()
        running_analysis_data["status"] = AnalysisStatus.RUNNING
        running_analysis = AnalysisVO(**running_analysis_data)
        
        self.mock_analysis_service.get_analysis_by_id.return_value = running_analysis
        
        # When
        with patch('analysis.interface.controller.analysis_controller.get_analysis_status') as mock_endpoint:
            mock_endpoint.return_value = {
                "analysis_id": running_analysis.id,
                "status": running_analysis.status,
                "ticker": running_analysis.ticker,
                "analysis_date": running_analysis.analysis_date,
                "created_at": running_analysis.created_at.isoformat(),
                "updated_at": running_analysis.updated_at.isoformat(),
                "error_message": running_analysis.error_message
            }
            
            response = self.client.get(f"/analysis/{analysis_id}/status")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["analysis_id"] == analysis_id
        assert response_data["status"] == AnalysisStatus.RUNNING.value
        assert response_data["ticker"] == "AAPL"

    def test_start_analysis_session_invalid_request_data(self):
        """분석 세션 시작 - 잘못된 요청 데이터 테스트"""
        # Given
        invalid_request_data = {
            "ticker": "",  # 빈 티커
            "analysis_date": "invalid-date",  # 잘못된 날짜 형식
            "analysts": ["invalid_analyst"],  # 잘못된 분석가 타입
            "research_depth": -1,  # 음수
        }
        
        # When
        response = self.client.post("/analysis/start", json=invalid_request_data)
        
        # Then
        assert response.status_code == 422  # Validation error

    def test_get_analysis_result_with_error_state(self):
        """분석 결과 조회 - 오류 상태 테스트"""
        # Given
        analysis_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        
        with patch('analysis.interface.controller.analysis_controller.get_current_member') as mock_auth:
            with patch('analysis.interface.controller.analysis_controller.Provide') as mock_provide:
                mock_auth.return_value = self.current_member
                mock_provide.__getitem__.return_value = self.mock_analysis_service
                
                failed_analysis_data = self.test_analysis_data.copy()
                failed_analysis_data.update({
                    "status": AnalysisStatus.FAILED,
                    "error_message": "Network connection failed",
                    "completed_at": datetime.now()
                })
                failed_analysis = AnalysisVO(**failed_analysis_data)
                
                self.mock_analysis_service.get_analysis_by_id.return_value = failed_analysis
                
                # When
                with patch('analysis.interface.controller.analysis_controller.get_analysis_result') as mock_endpoint:
                    mock_endpoint.return_value = AnalysisResultResponse(
                        id=failed_analysis.id,
                        ticker=failed_analysis.ticker,
                        analysis_date=failed_analysis.analysis_date.isoformat(),
                        status=failed_analysis.status,
                        market_report=failed_analysis.market_report,
                        news_report=failed_analysis.news_report,
                        fundamentals_report=failed_analysis.fundamentals_report,
                        investment_debate_state=failed_analysis.investment_debate_state,
                        trader_investment_plan=failed_analysis.trader_investment_plan,
                        risk_debate_state=failed_analysis.risk_debate_state,
                        final_trade_decision=failed_analysis.final_trade_decision,
                        final_report=failed_analysis.final_report,
                        created_at=failed_analysis.created_at.isoformat(),
                        completed_at=failed_analysis.completed_at.isoformat() if failed_analysis.completed_at else None,
                        error_message=failed_analysis.error_message
                    )
                    
                    response = self.client.get(f"/analysis/{analysis_id}")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == AnalysisStatus.FAILED.value
        assert response_data["error_message"] == "Network connection failed"

    @pytest.mark.asyncio
    async def test_websocket_endpoint_success(self):
        """WebSocket 연결 성공 테스트"""
        # Given
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Setup message sequence: ping, then disconnect
        mock_websocket.receive_text.side_effect = ["ping", WebSocketDisconnect()]
        
        with patch('analysis.interface.controller.analysis_controller.get_current_member') as mock_auth:
            with patch('analysis.interface.controller.analysis_controller.Provide') as mock_provide:
                mock_auth.return_value = self.current_member
                mock_provide.__getitem__.return_value = self.mock_websocket_manager
                
                self.mock_websocket_manager.connect = AsyncMock()
                self.mock_websocket_manager.disconnect = Mock()
                
                # Import the actual function to test
                from analysis.interface.controller.analysis_controller import websocket_endpoint
                
                # When
                await websocket_endpoint(mock_websocket, self.current_member, self.mock_websocket_manager)
        
        # Then
        self.mock_websocket_manager.connect.assert_called_once_with(mock_websocket, self.current_member.id)
        self.mock_websocket_manager.disconnect.assert_called_once_with(mock_websocket, self.current_member.id)
        mock_websocket.send_text.assert_called_once_with("pong")

    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection_error(self):
        """WebSocket 연결 오류 테스트"""
        # Given
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.close = AsyncMock()
        
        with patch('analysis.interface.controller.analysis_controller.get_current_member') as mock_auth:
            with patch('analysis.interface.controller.analysis_controller.Provide') as mock_provide:
                mock_auth.side_effect = Exception("Authentication failed")
                mock_provide.__getitem__.return_value = self.mock_websocket_manager
                
                # Import the actual function to test
                from analysis.interface.controller.analysis_controller import websocket_endpoint
                
                # When
                await websocket_endpoint(mock_websocket, self.current_member, self.mock_websocket_manager)
        
        # Then
        mock_websocket.close.assert_called_once_with(code=1011, reason="Authentication failed")

    def test_request_validation_edge_cases(self):
        """요청 데이터 검증 엣지 케이스 테스트"""
        test_cases = [
            {
                "name": "Empty ticker",
                "data": {"ticker": ""},
                "expected_status": 422
            },
            {
                "name": "Invalid research depth",
                "data": {"research_depth": 0},
                "expected_status": 422
            },
            {
                "name": "Invalid LLM provider",
                "data": {"llm_provider": ""},
                "expected_status": 422
            },
            {
                "name": "Invalid URL format",
                "data": {"backend_url": "not-a-url"},
                "expected_status": 422
            }
        ]
        
        for case in test_cases:
            # Given
            request_data = {
                "ticker": "AAPL",
                "analysis_date": "2024-01-01",
                "analysts": ["market"],
                "research_depth": 1,
                "llm_provider": "openai",
                "backend_url": "http://localhost:8000",
                "shallow_thinker": "gpt-3.5-turbo",
                "deep_thinker": "gpt-4"
            }
            request_data.update(case["data"])
            
            # When
            response = self.client.post("/analysis/start", json=request_data)
            
            # Then
            assert response.status_code == case["expected_status"], f"Failed for case: {case['name']}"

    def test_authentication_required_endpoints(self):
        """인증이 필요한 엔드포인트 테스트"""
        endpoints = [
            ("GET", "/analysis/"),
            ("POST", "/analysis/start"),
            ("GET", "/analysis/test-id"),
            ("GET", "/analysis/test-id/status")
        ]
        
        for method, endpoint in endpoints:
            # When - No authentication
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            
            # Then - Should return 401 or redirect to login
            assert response.status_code in [401, 422], f"Endpoint {method} {endpoint} should require authentication"