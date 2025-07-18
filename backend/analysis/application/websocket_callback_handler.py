from typing import Dict, Any, Optional, List, Union
from uuid import UUID
import json
import logging
import asyncio
from datetime import datetime

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from langchain_core.agents import AgentAction, AgentFinish

from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class WebSocketCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for streaming LangGraph agent events via WebSocket."""
    
    def __init__(self, websocket_manager: WebSocketManager, analysis_id: str):
        """Initialize the callback handler.
        
        Args:
            websocket_manager: WebSocket manager instance for sending messages
            analysis_id: ID of the analysis being performed
        """
        super().__init__()
        self.websocket_manager = websocket_manager
        self.analysis_id = analysis_id
        self.active_runs = {}  # Track active runs by run_id
        
    async def _send_event(self, event_type: str, data: Dict[str, Any]):
        """Send an event through WebSocket.
        
        Args:
            event_type: Type of event (e.g., 'llm_start', 'tool_start', etc.)
            data: Event data to send
        """
        try:
            await self.websocket_manager.send_analysis_update(
                analysis_id=self.analysis_id,
                update_type=event_type,
                data=data
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")
    
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM starts running."""
        agent_name = metadata.get("agent_name", "Unknown Agent") if metadata else "Unknown Agent"
        self.active_runs[run_id] = {
            "agent_name": agent_name,
            "start_time": datetime.now()
        }
        
        await self._send_event("llm_start", {
            "agent_name": agent_name,
            "prompts": prompts[:3] if prompts else [],  # Limit number of prompts sent
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[Dict, BaseMessage]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run on new LLM token. Only used for streaming."""
        run_info = self.active_runs.get(run_id, {})
        agent_name = run_info.get("agent_name", "Unknown Agent")
        
        await self._send_event("llm_token", {
            "agent_name": agent_name,
            "token": token,
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends running."""
        run_info = self.active_runs.get(run_id, {})
        agent_name = run_info.get("agent_name", "Unknown Agent")
        
        # Extract the response text
        response_text = ""
        if response.generations:
            for generation in response.generations[0]:
                response_text = generation.text
                break
        
        await self._send_event("llm_end", {
            "agent_name": agent_name,
            "response": response_text[:1000],  # Limit response size
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean up run info
        self.active_runs.pop(run_id, None)
    
    async def on_llm_error(
        self,
        error: Exception,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors."""
        run_info = self.active_runs.get(run_id, {})
        agent_name = run_info.get("agent_name", "Unknown Agent")
        
        await self._send_event("llm_error", {
            "agent_name": agent_name,
            "error": str(error),
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean up run info
        self.active_runs.pop(run_id, None)
    
    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when a chat model starts running."""
        # For chat models, we'll treat this similarly to on_llm_start
        agent_name = metadata.get("agent_name", "Unknown Agent") if metadata else "Unknown Agent"
        self.active_runs[run_id] = {
            "agent_name": agent_name,
            "start_time": datetime.now()
        }
        
        # Extract prompts from messages
        prompts = []
        if messages:
            for message_list in messages:
                for message in message_list:
                    prompts.append(message.content if hasattr(message, 'content') else str(message))
        
        await self._send_event("llm_start", {
            "agent_name": agent_name,
            "prompts": prompts[:3],  # Limit number of prompts sent
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool starts running."""
        tool_name = serialized.get("name", "Unknown Tool")
        agent_name = metadata.get("agent_name", "Unknown Agent") if metadata else "Unknown Agent"
        
        self.active_runs[run_id] = {
            "tool_name": tool_name,
            "agent_name": agent_name,
            "start_time": datetime.now()
        }
        
        await self._send_event("tool_start", {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "input": input_str[:500],  # Limit input size
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool ends running."""
        run_info = self.active_runs.get(run_id, {})
        tool_name = run_info.get("tool_name", "Unknown Tool")
        agent_name = run_info.get("agent_name", "Unknown Agent")
        
        await self._send_event("tool_end", {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "output": output[:1000],  # Limit output size
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean up run info
        self.active_runs.pop(run_id, None)
    
    async def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool errors."""
        run_info = self.active_runs.get(run_id, {})
        tool_name = run_info.get("tool_name", "Unknown Tool")
        agent_name = run_info.get("agent_name", "Unknown Agent")
        
        await self._send_event("tool_error", {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "error": str(error),
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean up run info
        self.active_runs.pop(run_id, None)
    
    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run on agent action."""
        await self._send_event("agent_action", {
            "tool": action.tool,
            "tool_input": str(action.tool_input)[:500],  # Limit input size
            "log": action.log,
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run on agent end."""
        await self._send_event("agent_finish", {
            "output": str(finish.return_values)[:1000],  # Limit output size
            "log": finish.log,
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain starts running."""
        chain_name = serialized.get("name", "Unknown Chain") if serialized else "Unknown Chain"
        
        await self._send_event("chain_start", {
            "chain_name": chain_name,
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain ends running."""
        await self._send_event("chain_end", {
            "outputs": str(outputs)[:1000],  # Limit output size
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_chain_error(
        self,
        error: Exception,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain errors."""
        await self._send_event("chain_error", {
            "error": str(error),
            "run_id": str(run_id),
            "timestamp": datetime.now().isoformat()
        })