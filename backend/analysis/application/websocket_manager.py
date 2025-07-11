from typing import Dict, Set
from fastapi import WebSocket
import json
from datetime import datetime
import logging
import asyncio
from utils.websocket_security import (
    WebSocketRateLimiter, 
    WebSocketMessageValidator,
    WebSocketConnectionManager
)
from config.config import get_settings
import uuid

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSocketManager:
    def __init__(self):
        # Store active connections by member_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store analysis_id to member_id mapping
        self.analysis_member_map: Dict[str, str] = {}
        
        # Initialize security components
        self.rate_limiter = WebSocketRateLimiter(
            max_messages_per_minute=settings.RATE_LIMIT_REQUESTS,
            max_message_size=10240  # 10KB
        )
        self.message_validator = WebSocketMessageValidator()
        self.connection_manager = WebSocketConnectionManager(
            connection_timeout=300,  # 5 minutes
            heartbeat_interval=30,   # 30 seconds
            max_connections_per_user=5
        )
        
        # Connection ID mapping
        self.websocket_to_connection_id: Dict[WebSocket, str] = {}
        self.member_websocket_map: Dict[str, Dict[str, WebSocket]] = {}
        
        # Start background tasks
        self._background_tasks = []

    async def start_background_tasks(self):
        """Start background tasks for security features"""
        self._background_tasks.append(
            asyncio.create_task(self.rate_limiter.start_cleanup_task())
        )
        self._background_tasks.append(
            asyncio.create_task(self.connection_manager.start_heartbeat_task())
        )

    async def stop_background_tasks(self):
        """Stop all background tasks"""
        await self.rate_limiter.stop_cleanup_task()
        await self.connection_manager.stop_heartbeat_task()
        
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def connect(self, websocket: WebSocket, member_id: str) -> bool:
        """Connect with enhanced security"""
        connection_id = str(uuid.uuid4())
        
        # Check connection limit
        if not await self.connection_manager.connect(member_id, connection_id, websocket):
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return False
        
        await websocket.accept()
        
        # Store connection mappings
        if member_id not in self.active_connections:
            self.active_connections[member_id] = set()
        self.active_connections[member_id].add(websocket)
        
        self.websocket_to_connection_id[websocket] = connection_id
        if member_id not in self.member_websocket_map:
            self.member_websocket_map[member_id] = {}
        self.member_websocket_map[member_id][connection_id] = websocket
        
        logger.info(f"WebSocket connected: member={member_id}, connection={connection_id}")
        return True

    async def disconnect(self, websocket: WebSocket, member_id: str):
        """Disconnect with cleanup"""
        connection_id = self.websocket_to_connection_id.get(websocket)
        if connection_id:
            await self.connection_manager.disconnect(member_id, connection_id)
            del self.websocket_to_connection_id[websocket]
            
            if member_id in self.member_websocket_map:
                self.member_websocket_map[member_id].pop(connection_id, None)
                if not self.member_websocket_map[member_id]:
                    del self.member_websocket_map[member_id]
        
        if member_id in self.active_connections:
            self.active_connections[member_id].discard(websocket)
            if not self.active_connections[member_id]:
                del self.active_connections[member_id]

    async def handle_message(self, websocket: WebSocket, member_id: str, message: str) -> dict:
        """Handle incoming message with validation and rate limiting"""
        connection_id = self.websocket_to_connection_id.get(websocket)
        if not connection_id:
            raise ValueError("Invalid connection")
        
        # Rate limiting
        if self.rate_limiter.is_rate_limited(connection_id):
            raise ValueError("Rate limit exceeded")
        
        # Message size validation
        if not self.rate_limiter.validate_message_size(message):
            raise ValueError("Message too large")
        
        # Parse and validate JSON
        data = self.message_validator.validate_json_message(message)
        if data is None:
            raise ValueError("Invalid JSON message")
        
        # Sanitize message
        sanitized_data = self.message_validator.sanitize_message(data)
        
        # Update heartbeat
        self.connection_manager.update_heartbeat(connection_id)
        
        return sanitized_data

    def register_analysis(self, analysis_id: str, member_id: str):
        """Register which member owns which analysis"""
        self.analysis_member_map[analysis_id] = member_id

    async def send_analysis_update(self, analysis_id: str, update_type: str, data: dict):
        """Send analysis update to the member who owns the analysis"""
        member_id = self.analysis_member_map.get(analysis_id)
        if not member_id:
            return
        
        message = {
            "type": "analysis_update",
            "analysis_id": analysis_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_to_member(member_id, message)

    async def send_to_member(self, member_id: str, message: dict|str):
        """Send message to all connections of a specific member"""
        if member_id not in self.active_connections:
            return
        
        dead_connections = set()
        for connection in self.active_connections[member_id]:
            try:
                if isinstance(message, dict):
                    await connection.send_json(message)
                else:
                    await connection.send_text(message)
            except Exception:
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            await self.disconnect(connection, member_id)