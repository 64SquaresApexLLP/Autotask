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
    try {
      return await apiService.get(API_ENDPOINTS.TECHNICIANS.GET_ALL);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get technician by ID
   */
  async getTechnicianById(technicianId) {
    try {
      return await apiService.get(API_ENDPOINTS.TECHNICIANS.GET_BY_ID(technicianId));
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get technician assignments
   */
  async getTechnicianAssignments(technicianId) {
    try {
      return await apiService.get(API_ENDPOINTS.TECHNICIANS.ASSIGNMENTS(technicianId));
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get technician workload statistics
   */
  async getTechnicianWorkload() {
    try {
      return await apiService.get(`${API_ENDPOINTS.TECHNICIANS.BASE}/workload`);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get available technicians for assignment
   */
  async getAvailableTechnicians() {
    try {
      return await apiService.get(`${API_ENDPOINTS.TECHNICIANS.BASE}/available`);
    } catch (error) {
      throw error;
    }
  }
};

export default technicianService;
