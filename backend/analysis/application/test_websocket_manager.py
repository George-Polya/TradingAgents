import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import WebSocket

from analysis.application.websocket_manager import WebSocketManager


class TestWebSocketManager:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.websocket_manager = WebSocketManager()
        self.mock_websocket = Mock(spec=WebSocket)
        self.mock_websocket.accept = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        
        self.test_member_id = "member_123"
        self.test_analysis_id = "analysis_456"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """웹소켓 연결 성공 테스트"""
        # Given
        member_id = self.test_member_id
        websocket = self.mock_websocket
        
        # When
        await self.websocket_manager.connect(websocket, member_id)
        
        # Then
        websocket.accept.assert_called_once()
        assert member_id in self.websocket_manager.active_connections
        assert websocket in self.websocket_manager.active_connections[member_id]

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_member(self):
        """같은 멤버의 여러 연결 테스트"""
        # Given
        member_id = self.test_member_id
        websocket1 = self.mock_websocket
        websocket2 = Mock(spec=WebSocket)
        websocket2.accept = AsyncMock()
        
        # When
        await self.websocket_manager.connect(websocket1, member_id)
        await self.websocket_manager.connect(websocket2, member_id)
        
        # Then
        assert member_id in self.websocket_manager.active_connections
        assert len(self.websocket_manager.active_connections[member_id]) == 2
        assert websocket1 in self.websocket_manager.active_connections[member_id]
        assert websocket2 in self.websocket_manager.active_connections[member_id]

    @pytest.mark.asyncio
    async def test_connect_multiple_members(self):
        """여러 멤버의 연결 테스트"""
        # Given
        member_id1 = "member_123"
        member_id2 = "member_456"
        websocket1 = self.mock_websocket
        websocket2 = Mock(spec=WebSocket)
        websocket2.accept = AsyncMock()
        
        # When
        await self.websocket_manager.connect(websocket1, member_id1)
        await self.websocket_manager.connect(websocket2, member_id2)
        
        # Then
        assert member_id1 in self.websocket_manager.active_connections
        assert member_id2 in self.websocket_manager.active_connections
        assert len(self.websocket_manager.active_connections[member_id1]) == 1
        assert len(self.websocket_manager.active_connections[member_id2]) == 1

    def test_disconnect_existing_connection(self):
        """기존 연결 해제 테스트"""
        # Given
        member_id = self.test_member_id
        websocket = self.mock_websocket
        self.websocket_manager.active_connections[member_id] = {websocket}
        
        # When
        self.websocket_manager.disconnect(websocket, member_id)
        
        # Then
        assert member_id not in self.websocket_manager.active_connections

    def test_disconnect_one_of_multiple_connections(self):
        """여러 연결 중 하나만 해제 테스트"""
        # Given
        member_id = self.test_member_id
        websocket1 = self.mock_websocket
        websocket2 = Mock(spec=WebSocket)
        self.websocket_manager.active_connections[member_id] = {websocket1, websocket2}
        
        # When
        self.websocket_manager.disconnect(websocket1, member_id)
        
        # Then
        assert member_id in self.websocket_manager.active_connections
        assert websocket1 not in self.websocket_manager.active_connections[member_id]
        assert websocket2 in self.websocket_manager.active_connections[member_id]

    def test_disconnect_non_existing_connection(self):
        """존재하지 않는 연결 해제 테스트"""
        # Given
        member_id = self.test_member_id
        websocket = self.mock_websocket
        
        # When
        self.websocket_manager.disconnect(websocket, member_id)
        
        # Then
        assert member_id not in self.websocket_manager.active_connections

    def test_disconnect_non_existing_member(self):
        """존재하지 않는 멤버 연결 해제 테스트"""
        # Given
        member_id = "non_existing_member"
        websocket = self.mock_websocket
        
        # When
        self.websocket_manager.disconnect(websocket, member_id)
        
        # Then
        assert member_id not in self.websocket_manager.active_connections

    def test_register_analysis_success(self):
        """분석 등록 성공 테스트"""
        # Given
        analysis_id = self.test_analysis_id
        member_id = self.test_member_id
        
        # When
        self.websocket_manager.register_analysis(analysis_id, member_id)
        
        # Then
        assert analysis_id in self.websocket_manager.analysis_member_map
        assert self.websocket_manager.analysis_member_map[analysis_id] == member_id

    def test_register_analysis_multiple(self):
        """여러 분석 등록 테스트"""
        # Given
        analysis_id1 = "analysis_123"
        analysis_id2 = "analysis_456"
        member_id1 = "member_123"
        member_id2 = "member_456"
        
        # When
        self.websocket_manager.register_analysis(analysis_id1, member_id1)
        self.websocket_manager.register_analysis(analysis_id2, member_id2)
        
        # Then
        assert self.websocket_manager.analysis_member_map[analysis_id1] == member_id1
        assert self.websocket_manager.analysis_member_map[analysis_id2] == member_id2

    def test_register_analysis_overwrite(self):
        """분석 등록 덮어쓰기 테스트"""
        # Given
        analysis_id = self.test_analysis_id
        member_id1 = "member_123"
        member_id2 = "member_456"
        
        # When
        self.websocket_manager.register_analysis(analysis_id, member_id1)
        self.websocket_manager.register_analysis(analysis_id, member_id2)
        
        # Then
        assert self.websocket_manager.analysis_member_map[analysis_id] == member_id2

    @pytest.mark.asyncio
    async def test_send_analysis_update_success(self):
        """분석 업데이트 전송 성공 테스트"""
        # Given
        analysis_id = self.test_analysis_id
        member_id = self.test_member_id
        update_type = "status_changed"
        data = {"status": "running", "progress": 50}
        
        # Register analysis and connection
        self.websocket_manager.register_analysis(analysis_id, member_id)
        self.websocket_manager.active_connections[member_id] = {self.mock_websocket}
        
        # When
        with patch('analysis.application.websocket_manager.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            await self.websocket_manager.send_analysis_update(analysis_id, update_type, data)
        
        # Then
        expected_message = {
            "type": "analysis_update",
            "analysis_id": analysis_id,
            "update_type": update_type,
            "data": data,
            "timestamp": mock_now.isoformat()
        }
        self.mock_websocket.send_json.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_send_analysis_update_unregistered_analysis(self):
        """등록되지 않은 분석 업데이트 전송 테스트"""
        # Given
        analysis_id = "unregistered_analysis"
        update_type = "status_changed"
        data = {"status": "running"}
        
        # When
        await self.websocket_manager.send_analysis_update(analysis_id, update_type, data)
        
        # Then
        self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_analysis_update_no_active_connections(self):
        """활성 연결이 없는 멤버에게 업데이트 전송 테스트"""
        # Given
        analysis_id = self.test_analysis_id
        member_id = self.test_member_id
        update_type = "status_changed"
        data = {"status": "running"}
        
        # Register analysis but no active connections
        self.websocket_manager.register_analysis(analysis_id, member_id)
        
        # When
        await self.websocket_manager.send_analysis_update(analysis_id, update_type, data)
        
        # Then
        self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_member_dict_message(self):
        """멤버에게 딕셔너리 메시지 전송 테스트"""
        # Given
        member_id = self.test_member_id
        message = {"type": "test", "data": "test_data"}
        self.websocket_manager.active_connections[member_id] = {self.mock_websocket}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        self.mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_member_string_message(self):
        """멤버에게 문자열 메시지 전송 테스트"""
        # Given
        member_id = self.test_member_id
        message = "test message"
        self.websocket_manager.active_connections[member_id] = {self.mock_websocket}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        self.mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_member_multiple_connections(self):
        """멤버의 여러 연결에 메시지 전송 테스트"""
        # Given
        member_id = self.test_member_id
        message = {"type": "test", "data": "test_data"}
        websocket1 = self.mock_websocket
        websocket2 = Mock(spec=WebSocket)
        websocket2.send_json = AsyncMock()
        
        self.websocket_manager.active_connections[member_id] = {websocket1, websocket2}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        websocket1.send_json.assert_called_once_with(message)
        websocket2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_member_non_existing_member(self):
        """존재하지 않는 멤버에게 메시지 전송 테스트"""
        # Given
        member_id = "non_existing_member"
        message = {"type": "test", "data": "test_data"}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_member_connection_error_cleanup(self):
        """연결 오류 시 정리 테스트"""
        # Given
        member_id = self.test_member_id
        message = {"type": "test", "data": "test_data"}
        
        # Mock websocket that raises exception
        broken_websocket = Mock(spec=WebSocket)
        broken_websocket.send_json = AsyncMock(side_effect=Exception("Connection error"))
        
        self.websocket_manager.active_connections[member_id] = {broken_websocket}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        # Connection should be cleaned up
        assert member_id not in self.websocket_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_to_member_partial_connection_error(self):
        """일부 연결 오류 시 정리 테스트"""
        # Given
        member_id = self.test_member_id
        message = {"type": "test", "data": "test_data"}
        
        # One good connection, one broken
        good_websocket = self.mock_websocket
        broken_websocket = Mock(spec=WebSocket)
        broken_websocket.send_json = AsyncMock(side_effect=Exception("Connection error"))
        
        self.websocket_manager.active_connections[member_id] = {good_websocket, broken_websocket}
        
        # When
        await self.websocket_manager.send_to_member(member_id, message)
        
        # Then
        # Good connection should still exist, broken should be removed
        assert member_id in self.websocket_manager.active_connections
        assert good_websocket in self.websocket_manager.active_connections[member_id]
        assert broken_websocket not in self.websocket_manager.active_connections[member_id]
        good_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_analysis_update_with_multiple_connections(self):
        """여러 연결에 분석 업데이트 전송 테스트"""
        # Given
        analysis_id = self.test_analysis_id
        member_id = self.test_member_id
        update_type = "progress_update"
        data = {"progress": 75, "step": "analysis"}
        
        websocket1 = self.mock_websocket
        websocket2 = Mock(spec=WebSocket)
        websocket2.send_json = AsyncMock()
        
        # Register analysis and multiple connections
        self.websocket_manager.register_analysis(analysis_id, member_id)
        self.websocket_manager.active_connections[member_id] = {websocket1, websocket2}
        
        # When
        with patch('analysis.application.websocket_manager.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            await self.websocket_manager.send_analysis_update(analysis_id, update_type, data)
        
        # Then
        expected_message = {
            "type": "analysis_update",
            "analysis_id": analysis_id,
            "update_type": update_type,
            "data": data,
            "timestamp": mock_now.isoformat()
        }
        websocket1.send_json.assert_called_once_with(expected_message)
        websocket2.send_json.assert_called_once_with(expected_message)

    def test_websocket_manager_initialization(self):
        """웹소켓 매니저 초기화 테스트"""
        # Given & When
        manager = WebSocketManager()
        
        # Then
        assert isinstance(manager.active_connections, dict)
        assert isinstance(manager.analysis_member_map, dict)
        assert len(manager.active_connections) == 0
        assert len(manager.analysis_member_map) == 0

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """전체 워크플로우 테스트"""
        # Given
        member_id = self.test_member_id
        analysis_id = self.test_analysis_id
        websocket = self.mock_websocket
        
        # When
        # 1. Connect
        await self.websocket_manager.connect(websocket, member_id)
        
        # 2. Register analysis
        self.websocket_manager.register_analysis(analysis_id, member_id)
        
        # 3. Send analysis update
        update_type = "status_changed"
        data = {"status": "completed"}
        
        with patch('analysis.application.websocket_manager.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            await self.websocket_manager.send_analysis_update(analysis_id, update_type, data)
        
        # 4. Disconnect
        self.websocket_manager.disconnect(websocket, member_id)
        
        # Then
        # Connection should be established and removed
        assert member_id not in self.websocket_manager.active_connections
        # Analysis mapping should still exist
        assert analysis_id in self.websocket_manager.analysis_member_map
        # Message should have been sent
        websocket.send_json.assert_called_once()