/**
 * Chatbot Service
 * Handles all chatbot-related API calls without authentication requirement
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
   * Get user's tickets (no authentication required)
   */
  async getMyTickets() {
    try {
      console.log('Fetching my tickets without authentication');
      return await this.makeRequest('/chatbot/tickets/my', {
        method: 'GET'
      });
    } catch (error) {
      console.error('Error in getMyTickets:', error);
      throw error;
    }
  },

  /**
   * Get detailed information for a specific ticket
   */
  async getTicketDetails(ticketId) {
    try {
      return await this.makeRequest(`/chatbot/tickets/${ticketId}`, {
        method: 'GET'
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Search for tickets based on criteria
   */
  async searchTickets(searchParams) {
    try {
      const queryString = new URLSearchParams(searchParams).toString();
      return await this.makeRequest(`/chatbot/tickets/search?${queryString}`, {
        method: 'GET'
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Find tickets similar to the specified ticket number
   */
  async getSimilarTickets(ticketNumber) {
    try {
      return await this.makeRequest(`/chatbot/tickets/similar/${ticketNumber}`, {
        method: 'GET'
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Send a chat message to the chatbot (no authentication required)
   */
  async sendChatMessage(message, context = {}) {
    try {
      return await this.makeRequest('/chatbot/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: message,
          session_id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          message_type: context.type || 'user',
          timestamp: new Date().toISOString()
        })
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get FAQ information
   */
  async getFAQ() {
    try {
      // Use the chat endpoint to get FAQ
      return await this.sendChatMessage('Show me frequently asked questions and help topics', {
        type: 'faq_request'
      });
    } catch (error) {
      throw error;
    }
  }
};

export default chatbotService;
