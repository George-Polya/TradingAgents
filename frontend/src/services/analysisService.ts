import api from './api';
import { 
  TradingAnalysisRequest, 
  AnalysisSessionResponse, 
  AnalysisResultResponse 
} from '../types';

export class AnalysisService {
  private static analysisCache: {
    data: AnalysisSessionResponse[] | null;
    timestamp: number;
  } = {
    data: null,
    timestamp: 0
  };
  
  private static CACHE_DURATION = 10000; // 10초 캐시
  
  static async getAnalysisList(forceRefresh: boolean = false): Promise<AnalysisSessionResponse[]> {
    const now = Date.now();
    
    // 캐시가 유효하고 강제 새로고침이 아닌 경우 캐시 데이터 반환
    if (!forceRefresh && this.analysisCache.data && 
        (now - this.analysisCache.timestamp) < this.CACHE_DURATION) {
      return this.analysisCache.data;
    }
    
    const response = await api.get<AnalysisSessionResponse[]>('/api/v1/analysis/');
    
    // 캐시 업데이트
    this.analysisCache = {
      data: response.data,
      timestamp: now
    };
    
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