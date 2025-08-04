/**
 * Authentication Service
 * Handles all authentication-related API calls
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

export const authService = {
  /**
   * Login user with username and password
   */
  async login(credentials) {
    try {
      const response = await apiService.post(API_ENDPOINTS.AUTH.LOGIN, credentials);
      
      if (response.access_token) {
        apiService.setAuthToken(response.access_token);
      }
      
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Logout user
   */
  async logout() {
    try {
      // Call logout endpoint if available
      await apiService.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', error.message);
    } finally {
      // Always remove token from storage
      apiService.removeAuthToken();
    }
  },

  /**
   * Get current user information
   */
  async getCurrentUser() {
    try {
      return await apiService.get(API_ENDPOINTS.AUTH.ME);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Refresh authentication token
   */
  async refreshToken() {
    try {
      const response = await apiService.post(API_ENDPOINTS.AUTH.REFRESH);
      
      if (response.access_token) {
        apiService.setAuthToken(response.access_token);
      }
      
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!apiService.getAuthToken();
  },

  /**
   * Get stored authentication token
   */
  getToken() {
    return apiService.getAuthToken();
  }
};

export default authService;
