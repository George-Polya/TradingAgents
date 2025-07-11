from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
import logging
import json
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class WebSocketRateLimiter:
    """WebSocket rate limiting implementation"""
    
    def __init__(self, max_messages_per_minute: int = 60, max_message_size: int = 10240):
        self.max_messages_per_minute = max_messages_per_minute
        self.max_message_size = max_message_size  # 10KB default
        self.message_counts: Dict[str, list] = defaultdict(list)
        self.blocked_clients: Dict[str, float] = {}
        self.cleanup_interval = 60  # Cleanup every minute
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the cleanup task for old message counts"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop the cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Cleanup old message counts periodically"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                current_time = time.time()
                
                # Clean up old message counts
                for client_id in list(self.message_counts.keys()):
                    self.message_counts[client_id] = [
                        timestamp for timestamp in self.message_counts[client_id]
                        if current_time - timestamp < 60
                    ]
                    if not self.message_counts[client_id]:
                        del self.message_counts[client_id]
                
                # Clean up expired blocks
                for client_id in list(self.blocked_clients.keys()):
                    if current_time > self.blocked_clients[client_id]:
                        del self.blocked_clients[client_id]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if a client is rate limited"""
        current_time = time.time()
        
        # Check if client is blocked
        if client_id in self.blocked_clients:
            if current_time < self.blocked_clients[client_id]:
                return True
            else:
                del self.blocked_clients[client_id]
        
        # Clean old timestamps
        self.message_counts[client_id] = [
            timestamp for timestamp in self.message_counts[client_id]
            if current_time - timestamp < 60
        ]
        
        # Check rate limit
        if len(self.message_counts[client_id]) >= self.max_messages_per_minute:
            # Block client for 1 minute
            self.blocked_clients[client_id] = current_time + 60
            logger.warning(f"Client {client_id} exceeded rate limit")
            return True
        
        # Record new message
        self.message_counts[client_id].append(current_time)
        return False
    
    def validate_message_size(self, message: str) -> bool:
        """Validate message size"""
        return len(message.encode('utf-8')) <= self.max_message_size


class WebSocketMessageValidator:
    """WebSocket message validation"""
    
    @staticmethod
    def validate_json_message(message: str) -> Optional[dict]:
        """Validate and parse JSON message"""
        try:
            data = json.loads(message)
            if not isinstance(data, dict):
                return None
            return data
        except json.JSONDecodeError:
            return None
    
    @staticmethod
    def sanitize_message(message: dict) -> dict:
        """Sanitize message content"""
        # Remove any potentially dangerous fields
        dangerous_fields = ['__proto__', 'constructor', 'prototype']
        
        def clean_dict(d):
            if not isinstance(d, dict):
                return d
            
            cleaned = {}
            for key, value in d.items():
                if key.lower() not in dangerous_fields:
                    if isinstance(value, dict):
                        cleaned[key] = clean_dict(value)
                    elif isinstance(value, list):
                        cleaned[key] = [clean_dict(item) if isinstance(item, dict) else item for item in value]
                    else:
                        cleaned[key] = value
            return cleaned
        
        return clean_dict(message)


class WebSocketConnectionManager:
    """Enhanced WebSocket connection manager with security features"""
    
    def __init__(self, 
                 connection_timeout: int = 300,  # 5 minutes
                 heartbeat_interval: int = 30,   # 30 seconds
                 max_connections_per_user: int = 5):
        self.connection_timeout = connection_timeout
        self.heartbeat_interval = heartbeat_interval
        self.max_connections_per_user = max_connections_per_user
        self.active_connections: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
        self.connection_times: Dict[str, datetime] = {}
        self.last_heartbeat: Dict[str, datetime] = {}
        self._heartbeat_task = None
    
    async def start_heartbeat_task(self):
        """Start the heartbeat monitoring task"""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def stop_heartbeat_task(self):
        """Stop the heartbeat task"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self):
        """Monitor connections and send heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                current_time = datetime.now()
                
                for member_id, connections in list(self.active_connections.items()):
                    for conn_id, websocket in list(connections.items()):
                        try:
                            # Check connection timeout
                            if conn_id in self.connection_times:
                                if (current_time - self.connection_times[conn_id]).seconds > self.connection_timeout:
                                    logger.info(f"Connection {conn_id} timed out")
                                    await self.disconnect(member_id, conn_id)
                                    continue
                            
                            # Send heartbeat
                            await websocket.send_json({"type": "heartbeat", "timestamp": current_time.isoformat()})
                            
                        except Exception as e:
                            logger.error(f"Error in heartbeat for {conn_id}: {e}")
                            await self.disconnect(member_id, conn_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def connect(self, member_id: str, connection_id: str, websocket: WebSocket) -> bool:
        """Connect a WebSocket with security checks"""
        # Check max connections per user
        if len(self.active_connections[member_id]) >= self.max_connections_per_user:
            logger.warning(f"User {member_id} exceeded max connections")
            return False
        
        self.active_connections[member_id][connection_id] = websocket
        self.connection_times[connection_id] = datetime.now()
        self.last_heartbeat[connection_id] = datetime.now()
        logger.info(f"WebSocket connected: member={member_id}, connection={connection_id}")
        return True
    
    async def disconnect(self, member_id: str, connection_id: str):
        """Disconnect a WebSocket"""
        if member_id in self.active_connections:
            if connection_id in self.active_connections[member_id]:
                del self.active_connections[member_id][connection_id]
                if not self.active_connections[member_id]:
                    del self.active_connections[member_id]
        
        if connection_id in self.connection_times:
            del self.connection_times[connection_id]
        
        if connection_id in self.last_heartbeat:
            del self.last_heartbeat[connection_id]
        
        logger.info(f"WebSocket disconnected: member={member_id}, connection={connection_id}")
    
    def update_heartbeat(self, connection_id: str):
        """Update last heartbeat time"""
        self.last_heartbeat[connection_id] = datetime.now()
        self.connection_times[connection_id] = datetime.now()  # Reset timeout
    
    async def send_to_member(self, member_id: str, message: dict):
        """Send message to all connections of a member"""
        if member_id in self.active_connections:
            dead_connections = []
            
            for conn_id, websocket in self.active_connections[member_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {conn_id}: {e}")
                    dead_connections.append(conn_id)
            
            # Clean up dead connections
            for conn_id in dead_connections:
                await self.disconnect(member_id, conn_id)