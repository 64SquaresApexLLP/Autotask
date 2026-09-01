import apiService from './api';

export const adminService = {
  // 1. User Management
  async getUsers() {
    return await apiService.get('/admin/users');
  },

  async createUser(userData) {
    return await apiService.post('/admin/users', userData);
  },

  async deleteUser(userId) {
    return await apiService.delete(`/admin/users/${userId}`);
  },

  // 2. Technician & Shift Management
  async getTechnicians() {
    return await apiService.get('/admin/technicians');
  },

  async createTechnician(techData) {
    return await apiService.post('/admin/technicians', techData);
  },

  async deleteTechnician(techId) {
    return await apiService.delete(`/admin/technicians/${techId}`);
  },

  async updateTechnicianScheduleAndSkills(techId, updateData) {
    return await apiService.put(`/admin/technicians/${techId}/schedule-skills`, updateData);
  },

  // 3. Reports
  async getMasterTicketsReport() {
    return await apiService.get('/admin/reports/master-tickets');
  },

  async getWiderMttrReport() {
    return await apiService.get('/admin/reports/wider-mttr');
  }
};
