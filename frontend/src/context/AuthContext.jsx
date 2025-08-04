import React, { createContext, useState, useEffect } from 'react';
import { authService } from '../services/authService.js';
import { ApiError } from '../services/api.js';

const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // Get from localStorage on initial load
    const storedUser = localStorage.getItem('user');
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize auth state on app load
  useEffect(() => {
    const initializeAuth = async () => {
      const token = authService.getToken();
      if (token && !user) {
        try {
          setLoading(true);
          const userData = await authService.getCurrentUser();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        } catch (error) {
          console.warn('Failed to get current user:', error.message);
          // Token might be expired, remove it
          authService.removeAuthToken();
          localStorage.removeItem('user');
        } finally {
          setLoading(false);
        }
      }
    };

    initializeAuth();
  }, [user]);

  const login = async (credentials) => {
    try {
      setLoading(true);
      setError(null);

      // Call backend authentication
      const response = await authService.login(credentials);

      // Create user object with the response data
      const userData = {
        username: credentials.username,
        role: credentials.role || 'user',
        token: response.access_token,
        ...response.user // Include any additional user data from backend
      };

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));

      return userData;
    } catch (error) {
      setError(error.message || 'Login failed');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await authService.logout();
    } catch (error) {
      console.warn('Logout API call failed:', error.message);
    } finally {
      setUser(null);
      localStorage.removeItem('user');
      setLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    clearError,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext, AuthProvider };
