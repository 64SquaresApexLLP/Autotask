/**
 * Services Index
 * Centralized export for all service modules
 */

export { default as apiService, ApiError } from './api.js';
export { default as authService } from './authService.js';
export { default as ticketService } from './ticketService.js';
export { default as technicianService } from './technicianService.js';

// Re-export for convenience
export { default as auth } from './authService.js';
export { default as tickets } from './ticketService.js';
export { default as technicians } from './technicianService.js';
