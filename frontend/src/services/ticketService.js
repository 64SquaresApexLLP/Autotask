/**
 * Ticket Service
 * Handles all ticket-related API calls
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

/**
 * Map technician IDs to display names (using real IDs from Snowflake)
 */
const TECHNICIAN_DISPLAY_MAP = {
  'T001': 'Technician T001',
  'T103': 'Technician T103',
  'T104': 'Technician T104',
  'T106': 'Technician T106'
};

/**
 * Transform backend ticket data to frontend format
 * Backend returns uppercase field names, frontend expects lowercase
 */
const transformTicketData = (ticket) => {
  if (!ticket) return null;

  // Use real technician ID from Snowflake
  const technicianId = ticket.TECHNICIAN_ID || ticket.technician_id;
  const assignedTechnician = technicianId; // Use the real ID directly
  const technicianDisplayName = technicianId ? (TECHNICIAN_DISPLAY_MAP[technicianId] || technicianId) : null;

  return {
    id: ticket.TICKETNUMBER || ticket.id,
    title: ticket.TITLE || ticket.title,
    description: ticket.DESCRIPTION || ticket.description,
    status: ticket.STATUS || ticket.status,
    priority: ticket.PRIORITY || ticket.priority,
    ticket_type: ticket.TICKETTYPE || ticket.ticket_type,
    ticket_category: ticket.TICKETCATEGORY || ticket.ticket_category,
    issue_type: ticket.ISSUETYPE || ticket.issue_type,
    sub_issue_type: ticket.SUBISSUETYPE || ticket.sub_issue_type,
    due_date: ticket.DUEDATETIME || ticket.due_date,
    resolution: ticket.RESOLUTION || ticket.resolution,
    user_id: ticket.USERID || ticket.user_id,
    user_email: ticket.USEREMAIL || ticket.user_email,
    requester_name: ticket.USERID || ticket.requester_name,
    phone_number: ticket.PHONENUMBER || ticket.phone_number,
    technician_id: technicianId,
    technician_email: ticket.TECHNICIANEMAIL || ticket.technician_email,
    assigned_technician: assignedTechnician,
    assigned_technician_display: technicianDisplayName,
    created_at: ticket.created_at || new Date().toISOString(),
    updated_at: ticket.updated_at || new Date().toISOString()
  };
};

export const ticketService = {
  /**
   * Get all tickets with optional filters
   */
  async getAllTickets(filters = {}) {
    try {
      const params = {};

      // Add filters to params
      if (filters.status) params.status = filters.status;
      if (filters.priority) params.priority = filters.priority;
      if (filters.limit) params.limit = filters.limit;
      if (filters.offset) params.offset = filters.offset;
      if (filters.assigned_technician) params.assigned_technician = filters.assigned_technician;
      if (filters.user_email) params.user_email = filters.user_email;

      const tickets = await apiService.get(API_ENDPOINTS.TICKETS.GET_ALL, params);

      // Transform the data to match frontend expectations
      return Array.isArray(tickets) ? tickets.map(transformTicketData) : [];
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get ticket by ID
   */
  async getTicketById(ticketId) {
    try {
      const ticket = await apiService.get(API_ENDPOINTS.TICKETS.GET_BY_ID(ticketId));
      return transformTicketData(ticket);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Create new ticket with extended timeout for agentic workflow
   */
  async createTicket(ticketData) {
    try {
      // Use extended timeout for ticket creation due to agentic workflow
      const ticket = await apiService.post(API_ENDPOINTS.TICKETS.CREATE, ticketData, {
        timeout: 120000 // 2 minutes timeout for agentic workflow
      });
      return transformTicketData(ticket);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Create ticket with optimistic updates and polling
   */
  async createTicketWithPolling(ticketData, onProgress) {
    try {
      // Start the ticket creation process
      const startTime = Date.now();

      // Notify progress
      if (onProgress) {
        onProgress({
          stage: 'submitting',
          message: 'Submitting your ticket...',
          progress: 10
        });
      }

      // Create ticket with extended timeout
      const createPromise = this.createTicket(ticketData);

      // Set up progress updates
      const progressInterval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(90, 10 + (elapsed / 120000) * 80); // Progress from 10% to 90% over 2 minutes

        let message = 'Processing your ticket...';
        if (elapsed > 20000) message = 'Analyzing your request with AI...';
        if (elapsed > 40000) message = 'Generating automated resolution...';
        if (elapsed > 60000) message = 'Finalizing ticket details...';
        if (elapsed > 90000) message = 'Almost done, please wait...';

        if (onProgress) {
          onProgress({
            stage: 'processing',
            message,
            progress: Math.round(progress),
            elapsed: Math.round(elapsed / 1000),
            isLongRunning: elapsed > 90000
          });
        }
      }, 2000);

      try {
        const ticket = await createPromise;
        clearInterval(progressInterval);

        if (onProgress) {
          onProgress({
            stage: 'completed',
            message: 'Ticket created successfully!',
            progress: 100
          });
        }

        return ticket;
      } catch (error) {
        clearInterval(progressInterval);
        throw error;
      }
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update existing ticket
   */
  async updateTicket(ticketId, updateData) {
    try {
      return await apiService.put(API_ENDPOINTS.TICKETS.UPDATE(ticketId), updateData);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Delete ticket
   */
  async deleteTicket(ticketId) {
    try {
      return await apiService.delete(API_ENDPOINTS.TICKETS.DELETE(ticketId));
    } catch (error) {
      throw error;
    }
  },

  /**
   * Assign ticket to technician
   */
  async assignTicket(ticketId, technicianId) {
    try {
      return await apiService.post(`/tickets/${ticketId}/assign`, {
        technician_id: technicianId
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get ticket statistics
   */
  async getTicketStatistics() {
    try {
      return await apiService.get(API_ENDPOINTS.TICKETS.STATISTICS);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get tickets assigned to current user (for technicians)
   */
  async getMyTickets() {
    try {
      return await apiService.get(API_ENDPOINTS.TICKETS.GET_ALL, {
        assigned_to_me: true
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get urgent tickets (high and critical priority)
   */
  async getUrgentTickets() {
    try {
      return await apiService.get(API_ENDPOINTS.TICKETS.GET_ALL, {
        priority: 'high,critical'
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update ticket status
   */
  async updateTicketStatus(ticketId, status) {
    try {
      return await apiService.patch(`/tickets/${ticketId}/status`, {
        status: status
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Add comment to ticket
   */
  async addTicketComment(ticketId, comment) {
    try {
      return await apiService.post(`${API_ENDPOINTS.TICKETS.GET_BY_ID(ticketId)}/comments`, {
        comment: comment
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Escalate ticket to management
   */
  async escalateTicket(ticketId, escalationData = {}) {
    try {
      return await apiService.post(`/tickets/${ticketId}/escalate`, escalationData);
    } catch (error) {
      throw error;
    }
  }
};

export default ticketService;
