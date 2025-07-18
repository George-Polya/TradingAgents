import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date

from analysis.application.analysis_service import AnalysisService
from analysis.application.websocket_manager import WebSocketManager
from analysis.application.websocket_callback_handler import WebSocketCallbackHandler
from analysis.application.websocket_messages import MessageType
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.domain.repository.analysis_repo import IAnalysisRepository
from analysis.infra.db_models.analysis import AnalysisStatus
from sqlmodel import Session
from ulid import ULID


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Test WebSocket callback handler integration with analysis service."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for the analysis service."""
        return {
            "analysis_repo": Mock(spec=IAnalysisRepository),
            "session": Mock(spec=Session),
            "ulid": Mock(spec=ULID),
            "websocket_manager": AsyncMock(spec=WebSocketManager)
        }
    
    @pytest.fixture
    def analysis_service(self, mock_dependencies):
        """Create an analysis service instance with mocked dependencies."""
        service = AnalysisService(
            analysis_repo=mock_dependencies["analysis_repo"],
            session=mock_dependencies["session"],
            ulid=mock_dependencies["ulid"],
            websocket_manager=mock_dependencies["websocket_manager"]
        )
        return service
    
    @pytest.fixture
    def test_analysis(self):
        """Create a test analysis object."""
        return AnalysisVO(
            id="test-analysis-123",
            member_id="member-123",
            ticker="AAPL",
            analysis_date=date(2024, 1, 1),
            analysts_selected=["news", "fundamentals"],
            research_depth=2,
            llm_provider="google",
            backend_url="https://api.example.com",
            shallow_thinker="gpt-3.5-turbo",
            deep_thinker="gpt-4",
            status=AnalysisStatus.RUNNING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @patch('analysis.application.analysis_service.TradingAgentsGraph')
    async def test_websocket_callback_handler_creation(
        self,
        mock_trading_graph_class,
        analysis_service,
        mock_dependencies,
        test_analysis
    ):
        """Test that WebSocketCallbackHandler is created and passed to graph.astream."""
        # Setup
        analysis_id = "test-analysis-123"
        mock_graph_instance = Mock()
        mock_graph_instance.propagator = Mock()
        mock_graph_instance.propagator.create_initial_state.return_value = {"test": "state"}
        mock_graph_instance.propagator.get_graph_args.return_value = {
            "stream_mode": "values",
            "config": {"recursion_limit": 100}
        }
        
        # Create async generator mock for astream
        async def mock_astream(*args, **kwargs):
            # Verify callbacks were passed
            assert "config" in kwargs
            assert "callbacks" in kwargs["config"]
            assert len(kwargs["config"]["callbacks"]) == 1
            assert isinstance(kwargs["config"]["callbacks"][0], WebSocketCallbackHandler)
            
            # Yield test chunks
            yield {"chunk": 1}
            yield {"chunk": 2}
        
        mock_graph_instance.graph = Mock()
        mock_graph_instance.graph.astream = mock_astream
        mock_graph_instance.process_signal = Mock(return_value="BUY")
        
        mock_trading_graph_class.return_value = mock_graph_instance
        
        # Mock repository update
        mock_dependencies["analysis_repo"].update.return_value = test_analysis
        
        # Execute
        await analysis_service._execute_trading_analysis(
            analysis_id,
            test_analysis,
            {"test": "config"}
        )
        
        # Verify WebSocket messages were sent
        websocket_manager = mock_dependencies["websocket_manager"]
        
        # Check analysis start message was sent
        start_call = websocket_manager.send_analysis_update.call_args_list[0]
        assert start_call[1]["update_type"] == MessageType.ANALYSIS_START.value
        assert start_call[1]["data"]["ticker"] == "AAPL"
        assert start_call[1]["data"]["analysts_selected"] == ["news", "fundamentals"]
        
        # Check analysis complete message was sent
        complete_call = websocket_manager.send_analysis_update.call_args_list[-1]
        assert complete_call[1]["update_type"] == MessageType.ANALYSIS_COMPLETE.value
        assert complete_call[1]["data"]["ticker"] == "AAPL"
        assert complete_call[1]["data"]["final_decision"] == "BUY"
    
    @patch('analysis.application.analysis_service.TradingAgentsGraph')
    async def test_websocket_callback_handler_not_created_when_no_manager(
        self,
        mock_trading_graph_class,
        mock_dependencies
    ):
        """Test that no callback handler is created when WebSocket manager is None."""
        # Setup service without WebSocket manager
        service = AnalysisService(
            analysis_repo=mock_dependencies["analysis_repo"],
            session=mock_dependencies["session"],
            ulid=mock_dependencies["ulid"],
            websocket_manager=None  # No WebSocket manager
        )
        
        # Create test analysis
        test_analysis = AnalysisVO(
            id="test-analysis-123",
            ticker="AAPL",
            analysis_date=date(2024, 1, 1),
            analysts_selected=["news"],
            research_depth=1,
            llm_provider="google"
        )
        
        # Setup mock graph
        mock_graph_instance = Mock()
        mock_graph_instance.propagator = Mock()
        mock_graph_instance.propagator.create_initial_state.return_value = {"test": "state"}
        mock_graph_instance.propagator.get_graph_args.return_value = {
            "stream_mode": "values",
            "config": {"recursion_limit": 100}
        }
        
        # Create async generator mock
        async def mock_astream(*args, **kwargs):
            # Verify no callbacks were passed
            if "config" in kwargs and "callbacks" in kwargs["config"]:
                assert len(kwargs["config"]["callbacks"]) == 0
            yield {"chunk": 1}
        
        mock_graph_instance.graph = Mock()
        mock_graph_instance.graph.astream = mock_astream
        mock_graph_instance.process_signal = Mock(return_value="HOLD")
        
        mock_trading_graph_class.return_value = mock_graph_instance
        mock_dependencies["analysis_repo"].update.return_value = test_analysis
        
        # Execute - should not raise any errors
        await service._execute_trading_analysis(
            "test-analysis-123",
            test_analysis,
            {"test": "config"}
        )
    
    @patch('analysis.application.analysis_service.TradingAgentsGraph')
    async def test_websocket_error_message_on_failure(
        self,
        mock_trading_graph_class,
        analysis_service,
        mock_dependencies,
        test_analysis
    ):
        """Test that error message is sent via WebSocket when analysis fails."""
        # Setup
        analysis_id = "test-analysis-123"
        error_message = "Test analysis failure"
        
        # Make graph raise an exception
        mock_trading_graph_class.side_effect = Exception(error_message)
        
        # Execute and expect exception
        with pytest.raises(Exception, match="Analysis execution failed"):
            await analysis_service._execute_trading_analysis(
                analysis_id,
                test_analysis,
                {"test": "config"}
            )
        
        # Verify error message was sent via WebSocket
        websocket_manager = mock_dependencies["websocket_manager"]
        
        # Check that error message was sent
        error_call = websocket_manager.send_analysis_update.call_args_list[-1]
        assert error_call[1]["update_type"] == MessageType.ANALYSIS_ERROR.value
        assert error_call[1]["data"]["error"] == error_message
        assert error_call[1]["data"]["phase"] == "analysis_execution"
    
    async def test_websocket_callback_handler_metadata_propagation(self):
        """Test that agent metadata is properly propagated through callbacks."""
        # Create WebSocket manager and callback handler
        websocket_manager = AsyncMock(spec=WebSocketManager)
        callback_handler = WebSocketCallbackHandler(
            websocket_manager=websocket_manager,
            analysis_id="test-123"
        )
        
        # Test LLM start with metadata
        from uuid import uuid4
        run_id = uuid4()
        
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Test prompt"],
            run_id=run_id,
            metadata={"agent_name": "Market Analyst"}
        )
        
        # Verify the correct message was sent
        websocket_manager.send_analysis_update.assert_called_once()
        call_args = websocket_manager.send_analysis_update.call_args
        
        assert call_args[1]["analysis_id"] == "test-123"
        assert call_args[1]["update_type"] == "llm_start"
        assert call_args[1]["data"]["agent_name"] == "Market Analyst"
        assert call_args[1]["data"]["run_id"] == str(run_id)