import { useEffect, useRef, useState, useCallback } from 'react';
import { AnalysisProgressUpdate } from '../types';
import { AnalysisService } from '../services/analysisService';

interface UseWebSocketProps {
  onProgressUpdate?: (update: AnalysisProgressUpdate) => void;
}

export const useWebSocket = ({ onProgressUpdate }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    // 이미 연결되어 있거나 연결 중이면 중복 연결 방지
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || 
                         wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    try {
      const ws = AnalysisService.createWebSocketConnection((data) => {
        if (data.type === 'progress_update') {
          onProgressUpdate?.(data.payload);
        } else if (data.type === 'error') {
          console.error('WebSocket error message:', data);
          setConnectionError(data.message || 'WebSocket error');
        }
      });

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        console.log('WebSocket connected');
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        console.log('WebSocket disconnected:', event.code, event.reason);
        // 비정상적인 종료인 경우 재연결 시도
        if (event.code !== 1000 && event.code !== 1001) {
          console.log('Abnormal close, will retry connection in 3 seconds');
          setTimeout(() => {
            if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
              connect();
            }
          }, 3000);
        }
      };

      ws.onerror = (error) => {
        setConnectionError('WebSocket connection error');
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      setConnectionError('Failed to create WebSocket connection');
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [onProgressUpdate]);

  const disconnect = () => {
    if (wsRef.current) {
      // 정상 종료 코드 사용
      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
      setIsConnected(false);
    }
  };

  useEffect(() => {
    // React strict mode에서 중복 실행 방지
    let mounted = true;
    
    if (mounted) {
      connect();
    }

    return () => {
      mounted = false;
      disconnect();
    };
  }, []); // connect 의존성 제거하여 재생성 방지

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
  };
};