import api from './api';
import tokenManager from './tokenManager';
import { CreateUserBody, LoginRequest, LoginResponse, Member } from '../types';

export class AuthService {
  static async register(userData: CreateUserBody): Promise<Member> {
    const response = await api.post<Member>('/api/v1/members', userData);
    return response.data;
  }

  static async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post<LoginResponse>('/api/v1/members/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    // Store tokens in memory
    tokenManager.setTokens(response.data.access_token, response.data.refresh_token);
    
    return response.data;
  }

  static async getCurrentUser(): Promise<Member> {
    const response = await api.get<Member>('/api/v1/members/me');
    return response.data;
  }

  static async logout(): Promise<void> {
    try {
      // Logout will use the refresh token from cookie
      await api.post('/api/v1/members/logout', {});
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    tokenManager.clearTokens();
  }

  static async refreshToken(): Promise<string | null> {
    try {
      // Refresh token using cookie
      const response = await api.post<{access_token: string, token_type: string}>('/api/v1/members/refresh', {});
      
      const newAccessToken = response.data.access_token;
      // Update access token in memory
      const currentRefreshToken = tokenManager.getRefreshToken() || 'cookie-based';
      tokenManager.setTokens(newAccessToken, currentRefreshToken);
      
      return newAccessToken;
    } catch (error) {
      console.error('Token refresh failed:', error);
      tokenManager.clearTokens();
      return null;
    }
  }

  static isAuthenticated(): boolean {
    return tokenManager.isAuthenticated();
  }

  static getAccessToken(): string | null {
    return tokenManager.getAccessToken();
  }

  static getRefreshToken(): string | null {
    return tokenManager.getRefreshToken();
  }
}