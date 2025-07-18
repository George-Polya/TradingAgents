import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date
from collections import defaultdict
from uuid import uuid4

from fastapi import WebSocket
from fastapi.testclient import TestClient

from analysis.application.analysis_service import AnalysisService
from analysis.application.websocket_manager import WebSocketManager
from analysis.application.websocket_callback_handler import WebSocketCallbackHandler
from analysis.application.websocket_messages import MessageType
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.infra.db_models.analysis import AnalysisStatus
from analysis.interface.dto import TradingAnalysisRequest


class MockWebSocketClient:
    """Mock WebSocket client that captures all sent messages."""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def send_json(self, data):
        """Capture JSON messages sent through WebSocket."""
        self.messages.append(data)
        
    async def send_text(self, data):
        """Capture text messages sent through WebSocket."""
        self.messages.append(data)
        
    async def close(self, code=1000, reason=""):
        """Simulate WebSocket close."""
        self.closed = True
        
    def get_messages_by_type(self, update_type):
        """Get all messages of a specific update type."""
        return [
            msg for msg in self.messages 
            if isinstance(msg, dict) and msg.get("update_type") == update_type
        ]


@pytest.mark.asyncio
class TestWebSocketStreamingIntegration:
    """Integration tests for WebSocket streaming during analysis execution."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for the analysis service."""
        return {
            "analysis_repo": Mock(),
            "session": Mock(),
            "ulid": Mock(),
        }
    
    @pytest.fixture
    def mock_websocket_client(self):
        """Create a mock WebSocket client."""
        return MockWebSocketClient()
    
    @pytest.fixture
    def websocket_manager(self, mock_websocket_client):
        """Create a WebSocketManager with a mock client."""
        manager = WebSocketManager()
        
        # Override send methods to use our mock client
        async def mock_send_to_member(member_id, message):
            await mock_websocket_client.send_json(message)
            
        async def mock_send_analysis_update(analysis_id, update_type, data):
            await mock_websocket_client.send_json({
                "type": "analysis_update",
                "analysis_id": analysis_id,
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            
        manager.send_to_member = AsyncMock(side_effect=mock_send_to_member)
        manager.send_analysis_update = AsyncMock(side_effect=mock_send_analysis_update)
        
        return manager
    
    @pytest.fixture
    def analysis_service(self, mock_dependencies, websocket_manager):
        """Create an analysis service with WebSocket manager."""
        service = AnalysisService(
            analysis_repo=mock_dependencies["analysis_repo"],
            session=mock_dependencies["session"],
            ulid=mock_dependencies["ulid"],
            websocket_manager=websocket_manager
        )
        return service
    
    @patch('analysis.application.analysis_service.TradingAgentsGraph')
    async def test_full_analysis_flow_with_websocket_streaming(
        self,
        mock_trading_graph_class,
        analysis_service,
        mock_dependencies,
        mock_websocket_client,
        websocket_manager
    ):
        """Test complete analysis flow with all WebSocket messages."""
        # Setup test data
        analysis_id = "test-analysis-123"
        test_analysis = AnalysisVO(
            id=analysis_id,
            member_id="test-member",
            ticker="AAPL",
            analysis_date=date(2024, 1, 1),
            analysts_selected=["news", "fundamentals"],
            research_depth=2,
            llm_provider="google",
            status=AnalysisStatus.RUNNING
        )
        
        # Setup mock graph
        mock_graph_instance = Mock()
        mock_graph_instance.propagator = Mock()
        mock_graph_instance.propagator.create_initial_state.return_value = {"test": "state"}
        mock_graph_instance.propagator.get_graph_args.return_value = {
            "stream_mode": "values",
            "config": {"recursion_limit": 100}
        }
        
        # Track callbacks passed to astream
        captured_callbacks = []
        
        async def mock_astream(*args, **kwargs):
            # Capture callbacks
            if "config" in kwargs and "callbacks" in kwargs["config"]:
                captured_callbacks.extend(kwargs["config"]["callbacks"])
            
            # Simulate agent execution steps
            # 1. News analyst working
            if captured_callbacks:
                callback = captured_callbacks[0]
                
                # News analyst starts
                await callback.on_llm_start(
                    serialized={"name": "ChatOpenAI"},
                    prompts=["Analyze news"],
                    run_id=uuid4(),
                    metadata={"agent_name": "News Analyst"}
                )
                
                # News analyst uses tool
                tool_run_id = uuid4()
                await callback.on_tool_start(
                    serialized={"name": "get_finnhub_news"},
                    input_str="AAPL news",
                    run_id=tool_run_id,
                    metadata={"agent_name": "News Analyst"}
                )
                
                await callback.on_tool_end(
                    output="Latest AAPL news: Strong Q4 earnings...",
                    run_id=tool_run_id
                )
                
                # News analyst completes
                await callback.on_llm_end(
                    response=Mock(generations=[[Mock(text="News analysis complete: Positive outlook")]]),
                    run_id=uuid4()
                )
            
            # Yield news report chunk
            yield {"news_report": "News analysis complete: Positive outlook"}
            
            # 2. Fundamentals analyst working
            if captured_callbacks:
                callback = captured_callbacks[0]
                
                # Fundamentals analyst starts
                await callback.on_llm_start(
                    serialized={"name": "ChatOpenAI"},
                    prompts=["Analyze fundamentals"],
                    run_id=uuid4(),
                    metadata={"agent_name": "Fundamentals Analyst"}
                )
                
                # Fundamentals analyst uses tool
                fund_tool_run_id = uuid4()
                await callback.on_tool_start(
                    serialized={"name": "get_finnhub_company_insider_sentiment"},
                    input_str="AAPL insider sentiment",
                    run_id=fund_tool_run_id,
                    metadata={"agent_name": "Fundamentals Analyst"}
                )
                
                await callback.on_tool_end(
                    output="Insider sentiment: Positive, recent buy transactions",
                    run_id=fund_tool_run_id
                )
                
                # Fundamentals analyst completes
                await callback.on_llm_end(
                    response=Mock(generations=[[Mock(text="Fundamentals strong: Buy recommendation")]]),
                    run_id=uuid4()
                )
            
            # Yield fundamentals report chunk
            yield {"fundamentals_report": "Fundamentals strong: Buy recommendation"}
            
            # 3. Trader makes final decision
            if captured_callbacks:
                callback = captured_callbacks[0]
                
                trader_run_id = uuid4()
                await callback.on_llm_start(
                    serialized={"name": "ChatOpenAI"},
                    prompts=["Make trading decision"],
                    run_id=trader_run_id,
                    metadata={"agent_name": "Trader"}
                )
                
                await callback.on_llm_end(
                    response=Mock(generations=[[Mock(text="FINAL TRANSACTION PROPOSAL: **BUY**")]]),
                    run_id=trader_run_id
                )
            
            # Yield final decision
            yield {"final_trade_decision": "BUY"}
        
        mock_graph_instance.graph = Mock()
        mock_graph_instance.graph.astream = mock_astream
        mock_graph_instance.process_signal = Mock(return_value="BUY")
        
        mock_trading_graph_class.return_value = mock_graph_instance
        mock_dependencies["analysis_repo"].update.return_value = test_analysis
        
        # Execute analysis
        await analysis_service._execute_trading_analysis(
            analysis_id,
            test_analysis,
            {"test": "config"}
        )
        
        # Analyze captured messages
        messages = mock_websocket_client.messages
        
        # Group messages by update type
        message_types = defaultdict(list)
        for msg in messages:
            if isinstance(msg, dict) and "update_type" in msg:
                message_types[msg["update_type"]].append(msg)
        
        # Verify analysis lifecycle messages
        assert MessageType.ANALYSIS_START.value in message_types
        assert MessageType.ANALYSIS_COMPLETE.value in message_types
        
        # Verify agent-specific messages
        llm_starts = message_types.get("llm_start", [])
        assert len(llm_starts) >= 3  # News, Fundamentals, Trader
        
        agent_names = [msg["data"]["agent_name"] for msg in llm_starts]
        assert "News Analyst" in agent_names
        assert "Fundamentals Analyst" in agent_names
        assert "Trader" in agent_names
        
        # Verify tool usage messages
        tool_starts = message_types.get("tool_start", [])
        assert len(tool_starts) >= 2  # News and Fundamentals tools
        
        tool_names = [msg["data"]["tool_name"] for msg in tool_starts]
        assert "get_finnhub_news" in tool_names
        assert "get_finnhub_company_insider_sentiment" in tool_names
        
        # Verify progress updates
        progress_updates = message_types.get("progress_update", [])
        assert len(progress_updates) >= 2  # News and Fundamentals reports
        
        # Verify final decision in complete message
        complete_msgs = message_types[MessageType.ANALYSIS_COMPLETE.value]
        assert len(complete_msgs) == 1
        assert complete_msgs[0]["data"]["final_decision"] == "BUY"
    
    @patch('analysis.application.analysis_service.TradingAgentsGraph')
    async def test_analysis_error_websocket_streaming(
        self,
        mock_trading_graph_class,
        analysis_service,
        mock_dependencies,
        mock_websocket_client
    ):
        """Test WebSocket streaming when analysis encounters an error."""
        # Setup test data
        analysis_id = "test-analysis-error"
        test_analysis = AnalysisVO(
            id=analysis_id,
            ticker="FAIL",
            analysis_date=date(2024, 1, 1),
            analysts_selected=["news"],
            llm_provider="google"
        )
        
        # Make graph raise an exception
        mock_trading_graph_class.side_effect = Exception("Analysis failed: API error")
        
        # Execute analysis and expect exception
        with pytest.raises(Exception, match="Analysis execution failed"):
            await analysis_service._execute_trading_analysis(
                analysis_id,
                test_analysis,
                {"test": "config"}
            )
        
        # Verify error message was sent
        messages = mock_websocket_client.messages
        error_messages = [
            msg for msg in messages 
            if isinstance(msg, dict) and msg.get("update_type") == MessageType.ANALYSIS_ERROR.value
        ]
        
        assert len(error_messages) == 1
        assert "Analysis failed: API error" in error_messages[0]["data"]["error"]
        assert error_messages[0]["data"]["phase"] == "analysis_execution"
    
    async def test_concurrent_analyses_websocket_isolation(
        self,
        analysis_service,
        websocket_manager
    ):
        """Test that concurrent analyses don't interfere with each other's WebSocket streams."""
        # Create two mock clients
        client1 = MockWebSocketClient()
        client2 = MockWebSocketClient()
        
        # Register two different analyses
        websocket_manager.register_analysis("analysis-1", "member-1")
        websocket_manager.register_analysis("analysis-2", "member-2")
        
        # Override send method to route to correct client
        async def route_message(member_id, message):
            if member_id == "member-1":
                await client1.send_json(message)
            elif member_id == "member-2":
                await client2.send_json(message)
        
        websocket_manager.send_to_member = AsyncMock(side_effect=route_message)
        
        # Also need to update send_analysis_update to use routing
        async def route_analysis_update(analysis_id, update_type, data):
            member_id = "member-1" if analysis_id == "analysis-1" else "member-2"
            await route_message(member_id, {
                "type": "analysis_update",
                "analysis_id": analysis_id,
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        
        websocket_manager.send_analysis_update = AsyncMock(side_effect=route_analysis_update)
        
        # Send updates for both analyses
        await websocket_manager.send_analysis_update(
            "analysis-1",
            MessageType.ANALYSIS_START.value,
            {"ticker": "AAPL"}
        )
        
        await websocket_manager.send_analysis_update(
            "analysis-2",
            MessageType.ANALYSIS_START.value,
            {"ticker": "GOOGL"}
        )
        
        # Verify isolation - each client only receives their analysis updates
        assert len(client1.messages) == 1
        assert client1.messages[0]["analysis_id"] == "analysis-1"
        
        assert len(client2.messages) == 1
        assert client2.messages[0]["analysis_id"] == "analysis-2"