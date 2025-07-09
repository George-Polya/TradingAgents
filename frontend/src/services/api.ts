import axios, { AxiosError } from 'axios';
import { ApiError } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      const currentPath = window.location.pathname;
      
      // 이미 로그인 페이지에 있으면 리다이렉트하지 않음
      if (currentPath !== '/login') {
        localStorage.removeItem('access_token');
        // React Router를 사용하여 페이지 이동
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;