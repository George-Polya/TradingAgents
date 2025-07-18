import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from langchain_core.outputs import LLMResult, Generation
from langchain_core.agents import AgentAction, AgentFinish

from .websocket_callback_handler import WebSocketCallbackHandler
from .websocket_manager import WebSocketManager


@pytest.mark.asyncio
class TestWebSocketCallbackHandler:
    """Test WebSocketCallbackHandler integration with WebSocketManager."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocketManager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_analysis_update = AsyncMock()
        return manager
    
    @pytest.fixture
    def callback_handler(self, mock_websocket_manager):
        """Create a WebSocketCallbackHandler instance."""
        analysis_id = "test-analysis-123"
        return WebSocketCallbackHandler(mock_websocket_manager, analysis_id)
    
    async def test_llm_lifecycle(self, callback_handler, mock_websocket_manager):
        """Test LLM start, token, and end events."""
        run_id = uuid4()
        
        # Test LLM start
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Test prompt"],
            run_id=run_id,
            metadata={"agent_name": "Market Analyst"}
        )
        
        # Verify start event was sent
        mock_websocket_manager.send_analysis_update.assert_called()
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["analysis_id"] == "test-analysis-123"
        assert call_args[1]["update_type"] == "llm_start"
        assert call_args[1]["data"]["agent_name"] == "Market Analyst"
        
        # Test LLM token
        await callback_handler.on_llm_new_token(
            token="Test token",
            run_id=run_id
        )
        
        # Test LLM end
        llm_result = LLMResult(
            generations=[[Generation(text="Test response")]]
        )
        await callback_handler.on_llm_end(
            response=llm_result,
            run_id=run_id
        )
        
        # Verify end event contains response
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "llm_end"
        assert "Test response" in last_call[1]["data"]["response"]
    
    async def test_llm_error(self, callback_handler, mock_websocket_manager):
        """Test LLM error handling."""
        run_id = uuid4()
        
        # Start LLM
        await callback_handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Test prompt"],
            run_id=run_id,
            metadata={"agent_name": "Technical Analyst"}
        )
        
        # Simulate error
        error = ValueError("Test error")
        await callback_handler.on_llm_error(
            error=error,
            run_id=run_id
        )
        
        # Verify error event
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "llm_error"
        assert last_call[1]["data"]["error"] == "Test error"
        assert last_call[1]["data"]["agent_name"] == "Technical Analyst"
    
    async def test_tool_lifecycle(self, callback_handler, mock_websocket_manager):
        """Test tool start, end, and error events."""
        run_id = uuid4()
        
        # Test tool start
        await callback_handler.on_tool_start(
            serialized={"name": "finnhub_search"},
            input_str="AAPL stock data",
            run_id=run_id,
            metadata={"agent_name": "Fundamentals Analyst"}
        )
        
        # Verify start event
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["update_type"] == "tool_start"
        assert call_args[1]["data"]["tool_name"] == "finnhub_search"
        assert call_args[1]["data"]["agent_name"] == "Fundamentals Analyst"
        
        # Test tool end
        await callback_handler.on_tool_end(
            output="Stock data result",
            run_id=run_id
        )
        
        # Verify end event
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "tool_end"
        assert "Stock data result" in last_call[1]["data"]["output"]
    
    async def test_agent_actions(self, callback_handler, mock_websocket_manager):
        """Test agent action and finish events."""
        run_id = uuid4()
        
        # Test agent action
        action = AgentAction(
            tool="search_provider",
            tool_input={"query": "AAPL news"},
            log="Searching for AAPL news"
        )
        await callback_handler.on_agent_action(
            action=action,
            run_id=run_id
        )
        
        # Verify action event
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["update_type"] == "agent_action"
        assert call_args[1]["data"]["tool"] == "search_provider"
        
        # Test agent finish
        finish = AgentFinish(
            return_values={"output": "Analysis complete"},
            log="Finished analysis"
        )
        await callback_handler.on_agent_finish(
            finish=finish,
            run_id=run_id
        )
        
        # Verify finish event
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "agent_finish"
        assert "Analysis complete" in last_call[1]["data"]["output"]
    
    async def test_chain_lifecycle(self, callback_handler, mock_websocket_manager):
        """Test chain start, end, and error events."""
        run_id = uuid4()
        
        # Test chain start
        await callback_handler.on_chain_start(
            serialized={"name": "TradingAnalysisChain"},
            inputs={"symbol": "AAPL"},
            run_id=run_id
        )
        
        # Verify start event
        call_args = mock_websocket_manager.send_analysis_update.call_args
        assert call_args[1]["update_type"] == "chain_start"
        assert call_args[1]["data"]["chain_name"] == "TradingAnalysisChain"
        
        # Test chain end
        await callback_handler.on_chain_end(
            outputs={"result": "Buy recommendation"},
            run_id=run_id
        )
        
        # Verify end event
        last_call = mock_websocket_manager.send_analysis_update.call_args_list[-1]
        assert last_call[1]["update_type"] == "chain_end"
        assert "Buy recommendation" in last_call[1]["data"]["outputs"]
    
    async def test_websocket_error_handling(self, callback_handler):
        """Test error handling when WebSocket fails."""
        # Create a manager that raises errors
        failing_manager = AsyncMock(spec=WebSocketManager)
        failing_manager.send_analysis_update = AsyncMock(
            side_effect=Exception("WebSocket error")
        )
        
        handler = WebSocketCallbackHandler(failing_manager, "test-123")
        run_id = uuid4()
        
        # This should not raise, errors should be logged
        await handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["Test"],
            run_id=run_id
        )
        
        # Verify the method was called despite the error
        failing_manager.send_analysis_update.assert_called_once()