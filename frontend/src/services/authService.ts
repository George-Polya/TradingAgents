import api from './api';
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
    
    // Store token in localStorage
    localStorage.setItem('access_token', response.data.access_token);
    
    return response.data;
  }

  static async getCurrentUser(): Promise<Member> {
    const response = await api.get<Member>('/api/v1/members/me');
    return response.data;
  }

  static logout(): void {
    localStorage.removeItem('access_token');
  }

  static isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}