import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Member } from '../types';
import { AuthService } from '../services/authService';

interface AuthContextType {
  user: Member | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<Member | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  const fetchUser = async () => {
    try {
      // First try to use existing access token
      if (AuthService.isAuthenticated()) {
        const userData = await AuthService.getCurrentUser();
        console.log('User data from API:', userData); // 디버깅용
        setUser(userData);
      } else {
        // If no access token, try to refresh using cookie
        const newToken = await AuthService.refreshToken();
        if (newToken) {
          const userData = await AuthService.getCurrentUser();
          console.log('User data from API after refresh:', userData);
          setUser(userData);
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch user:', error);
      // 401 에러일 때만 로그아웃 처리
      if (error.response?.status === 401) {
        // Try to refresh token one more time
        try {
          const newToken = await AuthService.refreshToken();
          if (newToken) {
            const userData = await AuthService.getCurrentUser();
            setUser(userData);
            return;
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
        }
        
        // If refresh also failed, logout
        await AuthService.logout();
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const response = await AuthService.login({ username: email, password });
      setUser(response.member);
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    await AuthService.logout();
    setUser(null);
  };

  const refetchUser = async () => {
    setIsLoading(true);
    await fetchUser();
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};