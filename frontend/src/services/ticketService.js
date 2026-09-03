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
  const assignedTechnician = technicianId || ticket.ASSIGNED_TECHNICIAN || ticket.assigned_technician || null;
  const technicianDisplayName = assignedTechnician ? (TECHNICIAN_DISPLAY_MAP[assignedTechnician] || assignedTechnician) : null;

    // Parse creation timestamp from Snowflake or ticket number
  let createdAt = ticket.CREATED_AT || ticket.created_at || ticket.DATE || ticket.date;
  if (!createdAt) {
    const tNum = String(ticket.TICKETNUMBER || ticket.ticket_number || ticket.id || '');
    if (/^T\d{8}\./.test(tNum)) {
      // Current format T{YYYYMMDD}.{seq} — only the creation date is encoded
      createdAt = `${tNum.substring(1, 5)}-${tNum.substring(5, 7)}-${tNum.substring(7, 9)}T00:00:00Z`;
    } else if (tNum.startsWith('T20') && tNum.length >= 15) {
      const yr = tNum.substring(1, 5);
      const mo = tNum.substring(5, 7);
      const dy = tNum.substring(7, 9);
      const hr = tNum.substring(9, 11);
      const mn = tNum.substring(11, 13);
      createdAt = `${yr}-${mo}-${dy}T${hr}:${mn}:00Z`;
    }
  }

  // Extract time spent (hours only)
  let timeSpent = ticket.TIME_SPENT || ticket.time_spent || null;
  const resolutionText = ticket.RESOLUTION || ticket.resolution || '';
  if (!timeSpent && resolutionText) {
    const match = String(resolutionText).match(/(?:\(|Time Spent:\s*|Logged Time Spent:\s*)(\d+(?:\.\d+)?\s*(?:hrs?|hours?|h))\)?/i);
    if (match) timeSpent = match[1];
  }

  // Numeric technician effort in hours (TIME_SPENT_HOURS column, written by the backend)
  const rawTimeSpentHours = ticket.TIME_SPENT_HOURS ?? ticket.time_spent_hours;
  const timeSpentHours = (rawTimeSpentHours !== null && rawTimeSpentHours !== undefined && rawTimeSpentHours !== '')
    ? Number(rawTimeSpentHours)
    : null;

  // Normalize priority: empty or legacy "Unknown" values fall back to Medium
  const rawPriority = ticket.PRIORITY || ticket.priority;
  const normalizedPriority = (rawPriority && String(rawPriority).trim().toLowerCase() !== 'unknown')
    ? rawPriority
    : 'Medium';

  return {
    id: ticket.TICKETNUMBER || ticket.ticket_number || ticket.id,
    title: ticket.TITLE || ticket.title || 'Untitled Ticket',
    description: ticket.DESCRIPTION || ticket.description || '',
    status: ticket.STATUS || ticket.status || 'Open',
    priority: normalizedPriority,
    ticket_type: ticket.TICKETTYPE || ticket.ticket_type,
    ticket_category: ticket.TICKETCATEGORY || ticket.ticket_category || ticket.ISSUETYPE || ticket.issue_type,
    category: ticket.TICKETCATEGORY || ticket.ticket_category || ticket.ISSUETYPE || ticket.issue_type || ticket.TICKETTYPE || 'General',
    issue_type: ticket.ISSUETYPE || ticket.issue_type,
    sub_issue_type: ticket.SUBISSUETYPE || ticket.sub_issue_type,
    due_date: ticket.DUEDATETIME || ticket.due_date,
    resolution: resolutionText,
    time_spent: timeSpent,
    time_spent_hours: timeSpentHours,
    user_id: ticket.USERID || ticket.user_id,
    user_email: ticket.USEREMAIL || ticket.user_email,
    requester_name: ticket.USERID || ticket.requester_name || ticket.USEREMAIL || ticket.user_email || 'User',
    phone_number: ticket.PHONENUMBER || ticket.phone_number,
    technician_id: technicianId,
    technician_email: ticket.TECHNICIANEMAIL || ticket.technician_email,
    assigned_technician: assignedTechnician,
    assigned_technician_display: technicianDisplayName,
    // AI pipeline output - only present on the ticket-creation response
    extracted_metadata: ticket.extracted_metadata || null,
    similar_tickets: ticket.similar_tickets || null,
    created_at: createdAt || new Date().toISOString(),
    resolved_at: ticket.RESOLVED_AT || ticket.resolved_at || ticket.COMPLETED_AT || ticket.completed_at || null,
    closed_at: ticket.CLOSED_AT || ticket.closed_at || null,
    assigned_at: ticket.ASSIGNED_AT || ticket.assigned_at || null,
    updated_at: ticket.UPDATED_AT || ticket.updated_at || new Date().toISOString()
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
   * Update ticket fields (status, priority, work note, time spent)
   */
  async updateTicket(ticketId, updateData = {}) {
    try {
      const cleanId = String(ticketId).replace('.', '-');
      return await apiService.patch(`/tickets/${cleanId}`, updateData);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update ticket status (with optional time spent)
   */
  async updateTicketStatus(ticketId, status, timeSpent = null) {
    try {
      const cleanId = String(ticketId).replace('.', '-');
      const payload = { status };
      if (timeSpent) payload.time_spent = timeSpent;
      return await apiService.patch(`/tickets/${cleanId}`, payload);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Add work note (with optional time spent)
   */
  async addWorkNote(ticketId, workNote, timeSpent = null) {
    try {
      const cleanId = String(ticketId).replace('.', '-');
      const payload = { work_note: workNote };
      if (timeSpent) payload.time_spent = timeSpent;
      return await apiService.patch(`/tickets/${cleanId}`, payload);
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
