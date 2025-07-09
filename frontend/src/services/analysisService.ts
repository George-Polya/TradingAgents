import api from './api';
import { 
  TradingAnalysisRequest, 
  AnalysisSessionResponse, 
  AnalysisResultResponse 
} from '../types';

export class AnalysisService {
  static async getAnalysisList(): Promise<AnalysisSessionResponse[]> {
    const response = await api.get<AnalysisSessionResponse[]>('/api/v1/analysis/');
    return response.data;
  }

  static async startAnalysis(request: TradingAnalysisRequest): Promise<AnalysisSessionResponse> {
    const response = await api.post<AnalysisSessionResponse>('/api/v1/analysis/start', request);
    return response.data;
  }

  static async getAnalysisResult(analysisId: string): Promise<AnalysisResultResponse> {
    const response = await api.get<AnalysisResultResponse>(`/api/v1/analysis/${analysisId}`);
    return response.data;
  }

  static async getAnalysisStatus(analysisId: string): Promise<any> {
    const response = await api.get(`/api/v1/analysis/${analysisId}/status`);
    return response.data;
  }

  static createWebSocketConnection(onMessage: (data: any) => void): WebSocket {
    const token = localStorage.getItem('access_token');
    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/api/v1/analysis/ws`;
    
    const ws = new WebSocket(`${wsUrl}?token=${token}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onopen = () => {
      console.log('WebSocket connected');
      // Send ping to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return ws;
  }
}