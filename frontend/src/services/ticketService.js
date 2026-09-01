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
  const assignedTechnician = technicianId || ticket.assigned_technician || null;
  const technicianDisplayName = assignedTechnician ? (TECHNICIAN_DISPLAY_MAP[assignedTechnician] || assignedTechnician) : null;

  return {
    id: ticket.TICKETNUMBER || ticket.ticket_number || ticket.id,
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
    // AI pipeline output - only present on the ticket-creation response
    extracted_metadata: ticket.extracted_metadata || null,
    similar_tickets: ticket.similar_tickets || null,
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
   * Update existing ticket (status, priority, and/or work note)
   */
  async updateTicket(ticketId, updateData) {
    try {
      return await apiService.patch(API_ENDPOINTS.TICKETS.UPDATE(ticketId), updateData);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Append a work note to the ticket's resolution log
   */
  async addWorkNote(ticketId, workNote) {
    try {
      return await apiService.patch(API_ENDPOINTS.TICKETS.UPDATE(ticketId), { work_note: workNote });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Send an update email to the ticket's customer
   */
  async emailCustomer(ticketId, message) {
    try {
      return await apiService.post(API_ENDPOINTS.TICKETS.EMAIL_CUSTOMER(ticketId), { message });
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
      return await apiService.patch(API_ENDPOINTS.TICKETS.UPDATE_STATUS(ticketId), {
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
  },

  /**
   * Find tickets similar to the given ticket, using real ticket data from
   * the existing /tickets API (no mock/hardcoded data). Similarity is scored
   * by matching issue type, ticket category, and priority against the same
   * fields on other tickets, excluding the ticket itself.
   */
  async getSimilarTickets(ticket, limit = 5) {
    if (!ticket) return [];

    try {
      const allTickets = await this.getAllTickets({ limit: 100 });

      const scored = allTickets
        .filter((t) => t.id && t.id !== ticket.id)
        .map((t) => {
          let score = 0;
          if (ticket.issue_type && t.issue_type && ticket.issue_type === t.issue_type) score += 3;
          if (ticket.sub_issue_type && t.sub_issue_type && ticket.sub_issue_type === t.sub_issue_type) score += 2;
          if (ticket.ticket_category && t.ticket_category && ticket.ticket_category === t.ticket_category) score += 2;
          if (ticket.priority && t.priority && ticket.priority.toLowerCase() === t.priority.toLowerCase()) score += 1;
          return { ticket: t, score };
        })
      return scored.slice(0, limit).map((entry) => entry.ticket);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get MTTR (Mean Time to Resolution) analytics and SLA metrics
   */
  async getMttrAnalytics(params = {}) {
    try {
      return await apiService.get(API_ENDPOINTS.ANALYTICS.MTTR, params);
    } catch (error) {
      throw error;
    }
  }
};

export default ticketService;
