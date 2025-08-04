/**
 * API Service Layer
 * Centralized HTTP client for making API requests
 */

import { API_BASE_URL, REQUEST_TIMEOUT, DEFAULT_HEADERS } from '../config/api.js';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.timeout = REQUEST_TIMEOUT;
    this.defaultHeaders = DEFAULT_HEADERS;
  }

  /**
   * Get authentication token from localStorage
   */
  getAuthToken() {
    return localStorage.getItem('authToken');
  }

  /**
   * Set authentication token in localStorage
   */
  setAuthToken(token) {
    localStorage.setItem('authToken', token);
  }

  /**
   * Remove authentication token from localStorage
   */
  removeAuthToken() {
    localStorage.removeItem('authToken');
  }

  /**
   * Get headers with authentication if available
   */
  getHeaders(customHeaders = {}) {
    const headers = { ...this.defaultHeaders, ...customHeaders };
    const token = this.getAuthToken();
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    return headers;
  }

  /**
   * Make HTTP request with error handling
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const timeout = options.timeout || this.timeout;
    const config = {
      headers: this.getHeaders(options.headers),
      ...options
    };

    // Remove timeout from config as it's not a fetch option
    delete config.timeout;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        ...config,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      // Handle non-200 responses
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new ApiError('Request timeout', 408);
      }
      
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Network or other errors
      throw new ApiError(
        error.message || 'Network error occurred',
        0,
        { originalError: error }
      );
    }
  }

  /**
   * GET request
   */
  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`);
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        url.searchParams.append(key, params[key]);
      }
    });
    
    return this.request(url.pathname + url.search, {
      method: 'GET'
    });
  }

  /**
   * POST request
   */
  async post(endpoint, data = null, options = {}) {
    const requestOptions = {
      method: 'POST',
      body: data ? JSON.stringify(data) : null,
      ...options
    };

    return this.request(endpoint, requestOptions);
  }

  /**
   * PUT request
   */
  async put(endpoint, data = null) {
    return this.request(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : null
    });
  }

  /**
   * PATCH request
   */
  async patch(endpoint, data = null) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : null
    });
  }

  /**
   * DELETE request
   */
  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE'
    });
  }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  constructor(message, status = 0, data = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }

  /**
   * Check if error is due to authentication issues
   */
  isAuthError() {
    return this.status === 401 || this.status === 403;
  }

  /**
   * Check if error is due to network issues
   */
  isNetworkError() {
    return this.status === 0 || this.status === 408;
  }

  /**
   * Check if error is a server error
   */
  isServerError() {
    return this.status >= 500;
  }

  /**
   * Check if error is a client error
   */
  isClientError() {
    return this.status >= 400 && this.status < 500;
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;
