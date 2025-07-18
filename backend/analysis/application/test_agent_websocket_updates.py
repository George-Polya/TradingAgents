import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from analysis.application.websocket_callback_handler import WebSocketCallbackHandler
from analysis.application.websocket_manager import WebSocketManager
from analysis.application.websocket_messages import MessageType


@pytest.mark.asyncio
class TestAgentWebSocketUpdates:
    """Test that agent-specific metadata is properly propagated through callbacks."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocketManager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_analysis_update = AsyncMock()
        return manager
    
    @pytest.fixture
    def callback_handler(self, mock_websocket_manager):
        """Create a WebSocketCallbackHandler instance."""
        return WebSocketCallbackHandler(
            websocket_manager=mock_websocket_manager,
            analysis_id="test-analysis-123"
        )
    
    async def test_news_analyst_metadata_propagation(self, callback_handler, mock_websocket_manager):
        """Test that News Analyst metadata is properly captured."""
        run_id = uuid4()
        
        # Simulate News Analyst starting
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Analyze news for AAPL"],
            run_id=run_id,
            metadata={
                "agent_name": "News Analyst",
                "step": "뉴스 데이터 수집 및 분석 중"
            }
        )
        
        # Verify the correct message was sent
        mock_websocket_manager.send_analysis_update.assert_called()
        call_args = mock_websocket_manager.send_analysis_update.call_args
        
        assert call_args[1]["update_type"] == "llm_start"
        assert call_args[1]["data"]["agent_name"] == "News Analyst"
        
        # Simulate tool usage
        await callback_handler.on_tool_start(
            serialized={"name": "get_finnhub_news"},
            input_str="AAPL news",
            run_id=uuid4(),
            metadata={"agent_name": "News Analyst"}
        )
        
        # Check tool start message
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "tool_start"
        assert last_call[1]["data"]["agent_name"] == "News Analyst"
        assert last_call[1]["data"]["tool_name"] == "get_finnhub_news"
    
    async def test_fundamentals_analyst_metadata_propagation(self, callback_handler, mock_websocket_manager):
        """Test that Fundamentals Analyst metadata is properly captured."""
        run_id = uuid4()
        
        # Simulate Fundamentals Analyst starting
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Analyze fundamentals for AAPL"],
            run_id=run_id,
            metadata={
                "agent_name": "Fundamentals Analyst",
                "step": "재무 데이터 수집 및 분석 중"
            }
        )
        
        # Verify the correct message was sent
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["data"]["agent_name"] == "Fundamentals Analyst"
        
        # Simulate tool usage
        await callback_handler.on_tool_start(
            serialized={"name": "get_finnhub_company_insider_sentiment"},
            input_str="AAPL insider sentiment",
            run_id=uuid4(),
            metadata={"agent_name": "Fundamentals Analyst"}
        )
        
        # Check tool message
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["data"]["agent_name"] == "Fundamentals Analyst"
        assert last_call[1]["data"]["tool_name"] == "get_finnhub_company_insider_sentiment"
    
    async def test_trader_metadata_propagation(self, callback_handler, mock_websocket_manager):
        """Test that Trader metadata is properly captured."""
        run_id = uuid4()
        
        # Simulate Trader making decision
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Make trading decision"],
            run_id=run_id,
            metadata={
                "agent_name": "Trader",
                "step": "투자 결정 분석 중"
            }
        )
        
        # Verify the correct message was sent
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["data"]["agent_name"] == "Trader"
        
        # Simulate final decision
        await callback_handler.on_llm_end(
            response=Mock(generations=[[Mock(text="FINAL TRANSACTION PROPOSAL: **BUY**")]]),
            run_id=run_id
        )
        
        # Check end message
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "llm_end"
        assert "BUY" in last_call[1]["data"]["response"]
    
    async def test_agent_without_metadata(self, callback_handler, mock_websocket_manager):
        """Test fallback behavior when agent metadata is not provided."""
        run_id = uuid4()
        
        # Simulate agent without metadata
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Some analysis"],
            run_id=run_id,
            metadata=None  # No metadata
        )
        
        # Should still send message with "Unknown Agent"
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["data"]["agent_name"] == "Unknown Agent"
    
    async def test_multiple_agents_concurrent_tracking(self, callback_handler, mock_websocket_manager):
        """Test that multiple agents can be tracked concurrently."""
        news_run_id = uuid4()
        fundamentals_run_id = uuid4()
        
        # Start both agents
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["News analysis"],
            run_id=news_run_id,
            metadata={"agent_name": "News Analyst"}
        )
        
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Fundamentals analysis"],
            run_id=fundamentals_run_id,
            metadata={"agent_name": "Fundamentals Analyst"}
        )
        
        # Verify both are tracked
        assert news_run_id in callback_handler.active_runs
        assert fundamentals_run_id in callback_handler.active_runs
        
        # End one agent
        await callback_handler.on_llm_end(
            response=Mock(generations=[[Mock(text="News report")]]),
            run_id=news_run_id
        )
        
        # Verify cleanup
        assert news_run_id not in callback_handler.active_runs
        assert fundamentals_run_id in callback_handler.active_runs