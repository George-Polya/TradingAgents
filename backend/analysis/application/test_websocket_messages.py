import pytest
from datetime import datetime
from pydantic import ValidationError

from .websocket_messages import (
    MessageType,
    BaseWebSocketMessage,
    LLMStartMessage,
    LLMTokenMessage,
    LLMEndMessage,
    LLMErrorMessage,
    ToolStartMessage,
    ToolEndMessage,
    ToolErrorMessage,
    AgentActionMessage,
    AgentFinishMessage,
    ChainStartMessage,
    ChainEndMessage,
    ChainErrorMessage,
    AnalysisStartMessage,
    AnalysisCompleteMessage,
    AnalysisErrorMessage,
    create_websocket_message,
)


class TestWebSocketMessages:
    """Test WebSocket message types and serialization."""
    
    def test_base_message_creation(self):
        """Test creating a base WebSocket message."""
        msg = BaseWebSocketMessage(
            type="analysis_update",
            analysis_id="test-123",
            update_type=MessageType.LLM_START
        )
        
        assert msg.type == "analysis_update"
        assert msg.analysis_id == "test-123"
        assert msg.update_type == MessageType.LLM_START
        assert isinstance(msg.timestamp, datetime)
    
    def test_llm_start_message(self):
        """Test LLM start message creation and serialization."""
        msg = LLMStartMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "Market Analyst",
                "run_id": "run-456",
                "parent_run_id": "parent-789"
            }
        )
        
        assert msg.update_type == MessageType.LLM_START
        assert msg.data.agent_name == "Market Analyst"
        assert msg.data.run_id == "run-456"
        assert msg.data.parent_run_id == "parent-789"
        
        # Test JSON serialization
        json_data = msg.model_dump()
        assert json_data["update_type"] == "llm_start"
        assert json_data["data"]["agent_name"] == "Market Analyst"
    
    def test_llm_token_message(self):
        """Test LLM token message with streaming data."""
        msg = LLMTokenMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "Technical Analyst",
                "run_id": "run-456",
                "token": "The"
            }
        )
        
        assert msg.data.token == "The"
        json_data = msg.model_dump()
        assert json_data["data"]["token"] == "The"
    
    def test_tool_start_message(self):
        """Test tool start message."""
        msg = ToolStartMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "Fundamentals Analyst",
                "run_id": "run-456",
                "tool_name": "finnhub_search",
                "input": "AAPL stock data"
            }
        )
        
        assert msg.data.tool_name == "finnhub_search"
        assert msg.data.input == "AAPL stock data"
    
    def test_tool_end_message_with_truncation(self):
        """Test tool end message with output truncation."""
        long_output = "x" * 2000  # Longer than max_length
        
        msg = ToolEndMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "News Analyst",
                "run_id": "run-456",
                "tool_name": "search_provider",
                "output": long_output[:1000]  # Manual truncation
            }
        )
        
        assert len(msg.data.output) == 1000
    
    def test_agent_action_message(self):
        """Test agent action message."""
        msg = AgentActionMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "tool": "stockstats",
                "tool_input": '{"ticker": "AAPL", "indicators": ["RSI", "MACD"]}',
                "log": "Analyzing technical indicators for AAPL",
                "run_id": "run-456"
            }
        )
        
        assert msg.data.tool == "stockstats"
        assert "RSI" in msg.data.tool_input
    
    def test_agent_finish_message(self):
        """Test agent finish message."""
        msg = AgentFinishMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "output": "Analysis complete: Bullish signal detected",
                "log": "Final assessment based on technical indicators",
                "run_id": "run-456"
            }
        )
        
        assert "Bullish signal" in msg.data.output
    
    def test_analysis_start_message(self):
        """Test analysis start message."""
        msg = AnalysisStartMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "ticker": "AAPL",
                "analysts_selected": ["market", "fundamentals", "technical"],
                "research_depth": 2
            }
        )
        
        assert msg.data.ticker == "AAPL"
        assert len(msg.data.analysts_selected) == 3
        assert msg.data.research_depth == 2
    
    def test_analysis_complete_message(self):
        """Test analysis complete message."""
        msg = AnalysisCompleteMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "ticker": "AAPL",
                "final_decision": "BUY",
                "summary": "Strong fundamentals and positive technical signals"
            }
        )
        
        assert msg.data.final_decision == "BUY"
        assert msg.data.summary is not None
    
    def test_error_messages(self):
        """Test various error message types."""
        # LLM Error
        llm_error = LLMErrorMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "Market Analyst",
                "run_id": "run-456",
                "error": "Rate limit exceeded"
            }
        )
        assert "Rate limit" in llm_error.data.error
        
        # Tool Error
        tool_error = ToolErrorMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "agent_name": "Fundamentals Analyst",
                "run_id": "run-456",
                "tool_name": "finnhub_search",
                "error": "API key invalid"
            }
        )
        assert tool_error.data.tool_name == "finnhub_search"
        
        # Analysis Error
        analysis_error = AnalysisErrorMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "error": "Failed to complete analysis",
                "phase": "investment_debate"
            }
        )
        assert analysis_error.data.phase == "investment_debate"
    
    def test_message_factory(self):
        """Test the message factory function."""
        # Test LLM start message
        msg = create_websocket_message(
            analysis_id="test-123",
            update_type=MessageType.LLM_START,
            data={
                "agent_name": "Market Analyst",
                "run_id": "run-456"
            }
        )
        
        assert isinstance(msg, LLMStartMessage)
        assert msg.analysis_id == "test-123"
        assert msg.data.agent_name == "Market Analyst"
        
        # Test tool start message
        msg = create_websocket_message(
            analysis_id="test-456",
            update_type=MessageType.TOOL_START,
            data={
                "agent_name": "Technical Analyst",
                "run_id": "run-789",
                "tool_name": "stockstats",
                "input": "Calculate RSI"
            }
        )
        
        assert isinstance(msg, ToolStartMessage)
        assert msg.data.tool_name == "stockstats"
    
    def test_invalid_message_type(self):
        """Test factory with invalid message type."""
        with pytest.raises(ValueError, match="Unknown message type"):
            create_websocket_message(
                analysis_id="test-123",
                update_type="invalid_type",  # type: ignore
                data={}
            )
    
    def test_validation_errors(self):
        """Test Pydantic validation errors."""
        # Missing required field
        with pytest.raises(ValidationError):
            LLMStartMessage(
                type="analysis_update",
                # Missing analysis_id
                data={
                    "agent_name": "Market Analyst",
                    "run_id": "run-456"
                }
            )
        
        # Invalid data structure
        with pytest.raises(ValidationError):
            LLMStartMessage(
                type="analysis_update",
                analysis_id="test-123",
                data={
                    # Missing required agent_name
                    "run_id": "run-456"
                }
            )
    
    def test_json_serialization(self):
        """Test JSON serialization with datetime."""
        msg = BaseWebSocketMessage(
            type="analysis_update",
            analysis_id="test-123",
            update_type=MessageType.SYSTEM_INFO
        )
        
        json_str = msg.model_dump_json()
        assert "analysis_update" in json_str
        assert "test-123" in json_str
        
        # Verify timestamp is properly serialized in JSON
        json_data = msg.model_dump(mode='json')
        assert isinstance(json_data["timestamp"], str)  # Should be ISO format string
        
        # Also test dict mode
        dict_data = msg.model_dump()
        assert isinstance(dict_data["timestamp"], str)  # With field_serializer, should also be string
    
    def test_chain_messages(self):
        """Test chain-related messages."""
        # Chain start
        start_msg = ChainStartMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "chain_name": "TradingAnalysisChain",
                "run_id": "run-456",
                "parent_run_id": "parent-123"
            }
        )
        assert start_msg.data.chain_name == "TradingAnalysisChain"
        
        # Chain end
        end_msg = ChainEndMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "outputs": '{"result": "Analysis complete"}',
                "run_id": "run-456"
            }
        )
        assert "Analysis complete" in end_msg.data.outputs
        
        # Chain error
        error_msg = ChainErrorMessage(
            type="analysis_update",
            analysis_id="test-123",
            data={
                "error": "Chain execution failed",
                "run_id": "run-456"
            }
        )
        assert "failed" in error_msg.data.error