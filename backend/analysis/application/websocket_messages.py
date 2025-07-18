from pydantic import BaseModel, Field, ConfigDict, field_serializer
from datetime import datetime
from typing import Dict, Any, Optional, Literal, Union
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types for agent activities."""
    # LLM events
    LLM_START = "llm_start"
    LLM_TOKEN = "llm_token"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"
    
    # Tool events
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    
    # Agent events
    AGENT_ACTION = "agent_action"
    AGENT_FINISH = "agent_finish"
    
    # Chain events
    CHAIN_START = "chain_start"
    CHAIN_END = "chain_end"
    CHAIN_ERROR = "chain_error"
    
    # Analysis events
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_ERROR = "analysis_error"
    
    # System events
    SYSTEM_INFO = "system_info"
    SYSTEM_ERROR = "system_error"


class BaseWebSocketMessage(BaseModel):
    """Base model for all WebSocket messages."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "analysis_update",
                "analysis_id": "abc-123",
                "update_type": "llm_start",
                "timestamp": "2024-01-18T10:30:45.123456"
            }
        }
    )
    
    type: str = Field(..., description="Type of the WebSocket message")
    analysis_id: str = Field(..., description="ID of the analysis")
    update_type: MessageType = Field(..., description="Specific type of update")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the event occurred")
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime, _info) -> str:
        """Serialize timestamp to ISO format string."""
        return timestamp.isoformat()


class AgentEventData(BaseModel):
    """Common data for agent-related events."""
    agent_name: str = Field(..., description="Name of the agent")
    run_id: str = Field(..., description="Unique ID for this run")
    parent_run_id: Optional[str] = Field(None, description="Parent run ID if nested")


# LLM Event Messages
class LLMStartMessage(BaseWebSocketMessage):
    """Message sent when an LLM starts processing."""
    update_type: Literal[MessageType.LLM_START] = MessageType.LLM_START
    data: AgentEventData


class LLMTokenMessage(BaseWebSocketMessage):
    """Message sent for streaming LLM tokens."""
    update_type: Literal[MessageType.LLM_TOKEN] = MessageType.LLM_TOKEN
    
    class TokenData(AgentEventData):
        token: str = Field(..., description="The token generated")
    
    data: TokenData


class LLMEndMessage(BaseWebSocketMessage):
    """Message sent when an LLM finishes processing."""
    update_type: Literal[MessageType.LLM_END] = MessageType.LLM_END
    
    class EndData(AgentEventData):
        response: str = Field(..., description="The LLM's response", max_length=1000)
    
    data: EndData


class LLMErrorMessage(BaseWebSocketMessage):
    """Message sent when an LLM encounters an error."""
    update_type: Literal[MessageType.LLM_ERROR] = MessageType.LLM_ERROR
    
    class ErrorData(AgentEventData):
        error: str = Field(..., description="Error message")
    
    data: ErrorData


# Tool Event Messages
class ToolStartMessage(BaseWebSocketMessage):
    """Message sent when a tool starts executing."""
    update_type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
    
    class ToolStartData(AgentEventData):
        tool_name: str = Field(..., description="Name of the tool")
        input: str = Field(..., description="Tool input", max_length=500)
    
    data: ToolStartData


class ToolEndMessage(BaseWebSocketMessage):
    """Message sent when a tool finishes executing."""
    update_type: Literal[MessageType.TOOL_END] = MessageType.TOOL_END
    
    class ToolEndData(AgentEventData):
        tool_name: str = Field(..., description="Name of the tool")
        output: str = Field(..., description="Tool output", max_length=1000)
    
    data: ToolEndData


class ToolErrorMessage(BaseWebSocketMessage):
    """Message sent when a tool encounters an error."""
    update_type: Literal[MessageType.TOOL_ERROR] = MessageType.TOOL_ERROR
    
    class ToolErrorData(AgentEventData):
        tool_name: str = Field(..., description="Name of the tool")
        error: str = Field(..., description="Error message")
    
    data: ToolErrorData


# Agent Event Messages
class AgentActionMessage(BaseWebSocketMessage):
    """Message sent when an agent takes an action."""
    update_type: Literal[MessageType.AGENT_ACTION] = MessageType.AGENT_ACTION
    
    class ActionData(BaseModel):
        tool: str = Field(..., description="Tool being used")
        tool_input: str = Field(..., description="Input to the tool", max_length=500)
        log: str = Field(..., description="Agent's reasoning")
        run_id: str = Field(..., description="Run ID")
    
    data: ActionData


class AgentFinishMessage(BaseWebSocketMessage):
    """Message sent when an agent finishes its task."""
    update_type: Literal[MessageType.AGENT_FINISH] = MessageType.AGENT_FINISH
    
    class FinishData(BaseModel):
        output: str = Field(..., description="Final output", max_length=1000)
        log: str = Field(..., description="Agent's final thoughts")
        run_id: str = Field(..., description="Run ID")
    
    data: FinishData


# Chain Event Messages
class ChainStartMessage(BaseWebSocketMessage):
    """Message sent when a chain starts executing."""
    update_type: Literal[MessageType.CHAIN_START] = MessageType.CHAIN_START
    
    class ChainData(BaseModel):
        chain_name: str = Field(..., description="Name of the chain")
        run_id: str = Field(..., description="Run ID")
        parent_run_id: Optional[str] = Field(None, description="Parent run ID")
    
    data: ChainData


class ChainEndMessage(BaseWebSocketMessage):
    """Message sent when a chain finishes executing."""
    update_type: Literal[MessageType.CHAIN_END] = MessageType.CHAIN_END
    
    class ChainEndData(BaseModel):
        outputs: str = Field(..., description="Chain outputs", max_length=1000)
        run_id: str = Field(..., description="Run ID")
    
    data: ChainEndData


class ChainErrorMessage(BaseWebSocketMessage):
    """Message sent when a chain encounters an error."""
    update_type: Literal[MessageType.CHAIN_ERROR] = MessageType.CHAIN_ERROR
    
    class ChainErrorData(BaseModel):
        error: str = Field(..., description="Error message")
        run_id: str = Field(..., description="Run ID")
    
    data: ChainErrorData


# Analysis Event Messages
class AnalysisStartMessage(BaseWebSocketMessage):
    """Message sent when an analysis starts."""
    update_type: Literal[MessageType.ANALYSIS_START] = MessageType.ANALYSIS_START
    
    class AnalysisStartData(BaseModel):
        ticker: str = Field(..., description="Stock ticker being analyzed")
        analysts_selected: list[str] = Field(..., description="Selected analysts")
        research_depth: int = Field(..., description="Research depth level")
    
    data: AnalysisStartData


class AnalysisCompleteMessage(BaseWebSocketMessage):
    """Message sent when an analysis completes."""
    update_type: Literal[MessageType.ANALYSIS_COMPLETE] = MessageType.ANALYSIS_COMPLETE
    
    class AnalysisCompleteData(BaseModel):
        ticker: str = Field(..., description="Stock ticker analyzed")
        final_decision: Optional[str] = Field(None, description="Final trade decision")
        summary: Optional[str] = Field(None, description="Analysis summary")
    
    data: AnalysisCompleteData


class AnalysisErrorMessage(BaseWebSocketMessage):
    """Message sent when an analysis encounters an error."""
    update_type: Literal[MessageType.ANALYSIS_ERROR] = MessageType.ANALYSIS_ERROR
    
    class AnalysisErrorData(BaseModel):
        error: str = Field(..., description="Error message")
        phase: Optional[str] = Field(None, description="Phase where error occurred")
    
    data: AnalysisErrorData


# Union type for all messages
WebSocketMessage = Union[
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
    AnalysisErrorMessage
]


# Message factory
def create_websocket_message(
    analysis_id: str,
    update_type: MessageType,
    data: Dict[str, Any]
) -> BaseWebSocketMessage:
    """Factory function to create appropriate message type."""
    message_classes = {
        MessageType.LLM_START: LLMStartMessage,
        MessageType.LLM_TOKEN: LLMTokenMessage,
        MessageType.LLM_END: LLMEndMessage,
        MessageType.LLM_ERROR: LLMErrorMessage,
        MessageType.TOOL_START: ToolStartMessage,
        MessageType.TOOL_END: ToolEndMessage,
        MessageType.TOOL_ERROR: ToolErrorMessage,
        MessageType.AGENT_ACTION: AgentActionMessage,
        MessageType.AGENT_FINISH: AgentFinishMessage,
        MessageType.CHAIN_START: ChainStartMessage,
        MessageType.CHAIN_END: ChainEndMessage,
        MessageType.CHAIN_ERROR: ChainErrorMessage,
        MessageType.ANALYSIS_START: AnalysisStartMessage,
        MessageType.ANALYSIS_COMPLETE: AnalysisCompleteMessage,
        MessageType.ANALYSIS_ERROR: AnalysisErrorMessage,
    }
    
    message_class = message_classes.get(update_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {update_type}")
    
    return message_class(
        type="analysis_update",
        analysis_id=analysis_id,
        update_type=update_type,
        data=data
    )