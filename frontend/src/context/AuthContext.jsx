import React, { createContext, useState, useEffect, useCallback } from 'react';
import { authService } from '../services/authService.js';
import { ApiError } from '../services/api.js';

const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem('user');
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Clear all auth state and send the user to the login page. */
  const forceLogout = useCallback(() => {
    authService.removeAuthToken();
    authService.logout().catch(() => {});
    setUser(null);
    localStorage.removeItem('user');
  }, []);

  // Initialize auth state on app load
  useEffect(() => {
    const initializeAuth = async () => {
      const token = authService.getToken();
      if (token && !user) {
        try {
          setLoading(true);
          const userData = await authService.getCurrentUser();
          const normalizedUser = {
            ...userData,
            // Ensure phone number is always present in the stored user,
            // backing it up from the legacy "phone" key if needed.
            phone_number: userData.phone_number || userData.phone || '',
          };
          setUser(normalizedUser);
          localStorage.setItem('user', JSON.stringify(normalizedUser));
        } catch (err) {
          console.warn('Failed to restore session:', err.message);
          // ApiService already tried a silent refresh – if we still get an
          // error here the refresh token is also gone, so clear everything.
          forceLogout();
        } finally {
          setLoading(false);
        }
      }
    };

    initializeAuth();
  }, [user, forceLogout]);

  // Listen for the "session expired" signal emitted by ApiService after a
  // failed silent refresh so we can redirect the user to the login page.
  useEffect(() => {
    const onSessionExpired = () => {
      console.warn('Session expired – logging out');
      forceLogout();
    };
    window.addEventListener('auth:session-expired', onSessionExpired);
    return () => window.removeEventListener('auth:session-expired', onSessionExpired);
  }, [forceLogout]);

  const login = async (credentials) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authService.login(credentials);

      const userData = {
        username: credentials.username,
        role: credentials.role || 'user',
        token: response.access_token,
        ...response.user,
        // Ensure phone number is always saved with the stored user in localStorage
        phone_number: response.user?.phone_number || response.user?.phone || '',
      };

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));

      return userData;
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await authService.logout();
    } catch (err) {
      console.warn('Logout API call failed:', err.message);
    } finally {
      setUser(null);
      localStorage.removeItem('user');
      setLoading(false);
    }
  };

  const clearError = () => setError(null);

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    clearError,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext, AuthProvider };
