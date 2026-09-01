/**
 * API Configuration
 * Centralized configuration for API endpoints and settings
 */

// Get base URL from environment variables
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

// API endpoints
export const API_ENDPOINTS = {
  // Authentication endpoints
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me'
  },
  
  // Ticket endpoints
  TICKETS: {
    BASE: '/tickets',
    CREATE: '/tickets',
    GET_ALL: '/tickets',
    GET_BY_ID: (id) => `/tickets/${id}`,
    UPDATE: (id) => `/tickets/${id}`,
    UPDATE_STATUS: (id) => `/tickets/${id}/status`,
    DELETE: (id) => `/tickets/${id}`,
    ASSIGN: (id) => `/tickets/${id}/assign`,
    EMAIL_CUSTOMER: (id) => `/tickets/${id}/email-customer`,
    STATISTICS: '/tickets/statistics'
  },
  
  // Technician endpoints
  TECHNICIANS: {
    BASE: '/technicians',
    GET_ALL: '/technicians',
    GET_BY_ID: (id) => `/technicians/${id}`,
    ASSIGNMENTS: (id) => `/technicians/${id}/assignments`
  },
  
  // Chatbot endpoints
  CHATBOT: {
    AUTH_LOGIN: '/chatbot/auth/login',
    MY_TICKETS: '/chatbot/tickets/my',  // Fixed: backend uses 'my' not 'my-tickets'
    TICKET_DETAILS: (ticketId) => `/chatbot/tickets/${ticketId}`,
    SEARCH_TICKETS: '/chatbot/tickets/search',
    SIMILAR_TICKETS: (ticketNumber) => `/chatbot/tickets/similar/${ticketNumber}`,
    CHAT: '/chatbot/chat',
    WEBSOCKET: '/ws'
  },

  // Analytics & SLA endpoints
  ANALYTICS: {
    MTTR: '/analytics/mttr'
  },

  // CTTC Network Ontology endpoints
  ONTOLOGY: {
    TOPOLOGY: '/ontology/topology',
    BLAST_RADIUS: (targetId) => `/ontology/blast-radius/${encodeURIComponent(targetId)}`,
    DATA: '/ontology/data',
    FULL_GRAPH: '/ontology/full-graph'
  }
};

// Request timeout in milliseconds
export const REQUEST_TIMEOUT = 30000;

// Default headers
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};
