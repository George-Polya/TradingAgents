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
    try {
      const ws = AnalysisService.createWebSocketConnection((data) => {
        if (data.type === 'progress_update') {
          onProgressUpdate?.(data.payload);
        }
      });

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        console.log('WebSocket connected');
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
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
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
    }
  };

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect]);

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
  };
};