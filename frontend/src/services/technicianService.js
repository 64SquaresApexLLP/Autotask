/**
 * Technician Service
 * Handles all technician-related API calls
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

export const technicianService = {
  /**
   * Get all technicians
   */
  async getAllTechnicians() {
    return await apiService.get(API_ENDPOINTS.TECHNICIANS.GET_ALL);
  },

  /**
   * Get technician by ID
   */
  async getTechnicianById(technicianId) {
    return await apiService.get(API_ENDPOINTS.TECHNICIANS.GET_BY_ID(technicianId));
  },

  /**
   * Get technician assignments
   */
  async getTechnicianAssignments(technicianId) {
    return await apiService.get(API_ENDPOINTS.TECHNICIANS.ASSIGNMENTS(technicianId));
  },

  /**
   * Get technician workload statistics
   */
  async getTechnicianWorkload() {
    return await apiService.get(`${API_ENDPOINTS.TECHNICIANS.BASE}/workload`);
  },

  /**
   * Get available technicians for assignment
   */
  async getAvailableTechnicians() {
    return await apiService.get(`${API_ENDPOINTS.TECHNICIANS.BASE}/available`);
  }
};

export default technicianService;
