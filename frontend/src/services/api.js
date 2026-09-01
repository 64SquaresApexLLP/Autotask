/**
 * API Service Layer
 * Centralized HTTP client for making API requests.
 * Includes automatic silent token refresh on 401 responses.
 */

import { API_BASE_URL, REQUEST_TIMEOUT, DEFAULT_HEADERS } from '../config/api.js';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.timeout = REQUEST_TIMEOUT;
    this.defaultHeaders = DEFAULT_HEADERS;

    // Prevents multiple concurrent refresh attempts racing each other.
    this._refreshPromise = null;
  }

  // ─── Token helpers ──────────────────────────────────────────────────────────

  getAuthToken() {
    return localStorage.getItem('authToken');
  }

  setAuthToken(token) {
    localStorage.setItem('authToken', token);
  }

  removeAuthToken() {
    localStorage.removeItem('authToken');
  }

  getRefreshToken() {
    return localStorage.getItem('refreshToken');
  }

  setRefreshToken(token) {
    localStorage.setItem('refreshToken', token);
  }

  removeRefreshToken() {
    localStorage.removeItem('refreshToken');
  }

  // ─── Headers ────────────────────────────────────────────────────────────────

  getHeaders(customHeaders = {}) {
    const headers = { ...this.defaultHeaders, ...customHeaders };
    const token = this.getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }

  // ─── Silent token refresh ────────────────────────────────────────────────────

  /**
   * Attempt to get a new access token using the stored refresh token.
   * Multiple simultaneous callers share a single in-flight request so we
   * never send duplicate refresh calls.
   *
   * @returns {Promise<string>} The new access token.
   * @throws  {ApiError} If the refresh fails (e.g. refresh token also expired).
   */
  async _silentRefresh() {
    if (this._refreshPromise) {
      // Another call is already refreshing – wait for it
      return this._refreshPromise;
    }

    this._refreshPromise = (async () => {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        throw new ApiError('No refresh token available', 401);
      }

      // Import lazily to avoid circular dependency
      const { API_ENDPOINTS } = await import('../config/api.js');

      const url = `${this.baseURL}${API_ENDPOINTS.AUTH.REFRESH}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { ...this.defaultHeaders },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || 'Token refresh failed',
          response.status,
          errorData
        );
      }

      const data = await response.json();

      this.setAuthToken(data.access_token);
      if (data.refresh_token) {
        this.setRefreshToken(data.refresh_token);
      }

      return data.access_token;
    })().finally(() => {
      this._refreshPromise = null;
    });

    return this._refreshPromise;
  }

  // ─── Core request ────────────────────────────────────────────────────────────

  /**
   * Make an HTTP request with automatic 401 → refresh → retry logic.
   *
   * @param {string}  endpoint
   * @param {object}  options   fetch options (method, body, headers, …)
   * @param {boolean} _isRetry  internal flag – prevents infinite refresh loops
   */
  async request(endpoint, options = {}, _isRetry = false) {
    const url = `${this.baseURL}${endpoint}`;
    const timeout = options.timeout || this.timeout;
    const config = {
      headers: this.getHeaders(options.headers),
      ...options,
    };
    delete config.timeout; // not a native fetch option

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, { ...config, signal: controller.signal });
      clearTimeout(timeoutId);

      // ── Auto-refresh on 401 ──────────────────────────────────────────────
      const isAuthEndpoint = endpoint.includes('/auth/login') || endpoint.includes('/auth/refresh');
      if (response.status === 401 && !_isRetry && !isAuthEndpoint) {
        try {
          await this._silentRefresh();
          // Retry with the new access token (update Authorization header)
          const retryConfig = {
            ...config,
            headers: this.getHeaders(options.headers),
          };
          const retryController = new AbortController();
          const retryTimeoutId = setTimeout(() => retryController.abort(), timeout);
          const retryResponse = await fetch(url, {
            ...retryConfig,
            signal: retryController.signal,
          });
          clearTimeout(retryTimeoutId);

          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => ({}));
            throw new ApiError(
              errorData.detail || `HTTP ${retryResponse.status}: ${retryResponse.statusText}`,
              retryResponse.status,
              errorData
            );
          }

          const contentType = retryResponse.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            return await retryResponse.json();
          }
          return await retryResponse.text();
        } catch (refreshError) {
          // Refresh itself failed – clear auth state, fire event so AuthContext
          // can redirect the user to the login page.
          this.removeAuthToken();
          this.removeRefreshToken();
          window.dispatchEvent(new CustomEvent('auth:session-expired'));
          throw new ApiError('Session expired. Please log in again.', 401);
        }
      }
      // ── End auto-refresh ─────────────────────────────────────────────────

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

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
      throw new ApiError(error.message || 'Network error occurred', 0, { originalError: error });
    }
  }

  // ─── Convenience methods ─────────────────────────────────────────────────────

  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`);
    Object.keys(params).forEach((key) => {
      if (params[key] !== undefined && params[key] !== null) {
        url.searchParams.append(key, params[key]);
      }
    });
    return this.request(url.pathname + url.search, { method: 'GET' });
  }

  async post(endpoint, data = null, options = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : null,
      ...options,
    });
  }

  async put(endpoint, data = null) {
    return this.request(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : null,
    });
  }

  async patch(endpoint, data = null) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : null,
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

// ─── Custom API Error ─────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(message, status = 0, data = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }

  isAuthError()    { return this.status === 401 || this.status === 403; }
  isNetworkError() { return this.status === 0   || this.status === 408; }
  isServerError()  { return this.status >= 500; }
  isClientError()  { return this.status >= 400 && this.status < 500; }
}

// ─── Singleton ────────────────────────────────────────────────────────────────
const apiService = new ApiService();
export default apiService;
