/**
 * Authentication Service
 * Handles all authentication-related API calls
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

export const authService = {
  /**
   * Login user with username and password.
   * Stores both the access token and the refresh token.
   */
  async login(credentials) {
    const response = await apiService.post(API_ENDPOINTS.AUTH.LOGIN, credentials);

    if (response.access_token) {
      apiService.setAuthToken(response.access_token);
    }
    if (response.refresh_token) {
      apiService.setRefreshToken(response.refresh_token);
    }

    return response;
  },

  /**
   * Logout user – clears both tokens locally and notifies the backend.
   */
  async logout() {
    try {
      await apiService.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch (error) {
      console.warn('Logout API call failed:', error.message);
    } finally {
      apiService.removeAuthToken();
      apiService.removeRefreshToken();
    }
  },

  /**
   * Get current user information.
   */
  async getCurrentUser() {
    return await apiService.get(API_ENDPOINTS.AUTH.ME);
  },

  /**
   * Manually request a new access token using the stored refresh token.
   * Normally this is called automatically by ApiService on 401 responses,
   * but you can call it proactively if needed.
   */
  async refreshToken() {
    const refreshToken = apiService.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiService.post(API_ENDPOINTS.AUTH.REFRESH, {
      refresh_token: refreshToken,
    });

    if (response.access_token) {
      apiService.setAuthToken(response.access_token);
    }
    if (response.refresh_token) {
      apiService.setRefreshToken(response.refresh_token);
    }

    return response;
  },

  /** Returns true when an access token is present in storage. */
  isAuthenticated() {
    return !!apiService.getAuthToken();
  },

  /** Returns the stored access token. */
  getToken() {
    return apiService.getAuthToken();
  },

  /** Expose so AuthContext can remove the token directly. */
  removeAuthToken() {
    apiService.removeAuthToken();
  },
};

export default authService;
