/**
 * Services Index
 * Centralized export for all service modules
 */

export { default as apiService, ApiError } from './api.js';
export { default as authService } from './authService.js';
export { default as ticketService } from './ticketService.js';
export { default as technicianService } from './technicianService.js';

// Re-export for convenience
export {
  authService as auth,
  ticketService as tickets,
  technicianService as technicians
};
