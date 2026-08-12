import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const response = await authApi.getCurrentUser();
      setUser(response.data);
    } catch (error) {
      console.error('Failed to load user profile:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const restoreSession = async () => {
    const refreshToken = localStorage.getItem('refresh_token');

    if (!refreshToken) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const response = await authApi.refreshToken(refreshToken);
      localStorage.setItem('access_token', response.data.access);
      await fetchProfile();
    } catch (error) {
      console.error('Failed to restore session:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setLoading(false);
    }
  };

  useEffect(() => {
    const bootAuth = async () => {
      const accessToken = localStorage.getItem('access_token');

      if (accessToken) {
        await fetchProfile();
        return;
      }

      await restoreSession();
    };

    bootAuth();
  }, []);

  const login = async ({ business_code, username, password }) => {
    const response = await authApi.login({ business_code, username, password });
    const { access, refresh, user: loggedInUser } = response.data;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setUser(loggedInUser);
    return response.data;
  };

  const register = async (registerData) => {
    const response = await authApi.register(registerData);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    window.location.href = '/login';
  };

  const hasRole = (roles) => {
    if (!user) return false;
    if (typeof roles === 'string') return user.role === roles;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        hasRole,
        refreshProfile: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
