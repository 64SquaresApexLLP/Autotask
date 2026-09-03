import apiService from './api';

export const adminService = {
  // 1. User Management (Standard Users & System Admins)
  async getUsers(role) {
    const params = role ? `?role=${role}` : '';
    return await apiService.get(`/admin/users${params}`);
  },

  async createUser(userData) {
    return await apiService.post('/admin/users', userData);
  },

  async deleteUser(userId) {
    return await apiService.delete(`/admin/users/${userId}`);
  },

  // 1b. Enterprise Admin Accounts (ADMIN_USERS table in Snowflake)
  async getAdminUsers() {
    return await apiService.get('/admin/admin-users');
  },

  async createAdminUser(adminData) {
    return await apiService.post('/admin/admin-users', adminData);
  },

  async deleteAdminUser(adminId) {
    return await apiService.delete(`/admin/admin-users/${adminId}`);
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
