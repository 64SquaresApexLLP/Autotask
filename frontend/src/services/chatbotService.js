/**
 * Chatbot Service
 * Handles all chatbot-related API calls
 */

import { API_BASE_URL } from '../config/api.js';

console.log('Chatbot Service - API Base URL:', API_BASE_URL);

export const chatbotService = {
  /**
   * Make direct API calls to avoid any middleware issues
   */
  async makeRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log('Making request to:', url, 'with options:', options);

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('API Response:', data);
    return data;
  },

  /**
   * Authenticate user for chatbot access
   */
  async login(credentials) {
    try {
      console.log('Chatbot login attempt:', credentials.username);
      return await this.makeRequest('/chatbot/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials)
      });
    } catch (error) {
      console.error('Chatbot login error:', error);
      throw error;
    }
  },

  /**
   * Get user's tickets
   */
  async getMyTickets(token) {
    try {
      console.log('Fetching my tickets with token:', token ? 'Token present' : 'No token');
      return await this.makeRequest('/chatbot/tickets/my', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      console.error('Error in getMyTickets:', error);
      throw error;
    }
  },

  /**
   * Get detailed information for a specific ticket
   */
  async getTicketDetails(ticketId, token) {
    try {
      return await this.makeRequest(`/chatbot/tickets/${ticketId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Search for tickets based on criteria
   */
  async searchTickets(searchParams, token) {
    try {
      const queryString = new URLSearchParams(searchParams).toString();
      return await this.makeRequest(`/chatbot/tickets/search?${queryString}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Find tickets similar to the specified ticket number
   */
  async getSimilarTickets(ticketNumber, token) {
    try {
      return await this.makeRequest(`/chatbot/tickets/similar/${ticketNumber}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Send a chat message to the chatbot
   */
  async sendChatMessage(message, token, context = {}) {
    try {
      return await this.makeRequest('/chatbot/chat', {
        method: 'POST',
        body: JSON.stringify({
          message,
          context
        }),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get FAQ information
   */
  async getFAQ(token) {
    try {
      // Use the chat endpoint to get FAQ
      return await this.sendChatMessage('Show me frequently asked questions and help topics', token, {
        type: 'faq_request'
      });
    } catch (error) {
      throw error;
    }
  }
};

export default chatbotService;
