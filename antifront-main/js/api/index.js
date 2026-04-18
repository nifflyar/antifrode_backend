/**
 * API module - Export all feature-specific API clients
 * Usage:
 *   import { dashboardApi, passengersApi, authApi, operationsApi } from './api/index.js';
 *   const summary = await dashboardApi.getSummary();
 */

// All modules are loaded via individual script tags in HTML
// This file serves as documentation for the API structure

const API = {
  dashboard: dashboardApi,
  passengers: passengersApi,
  auth: authApi,
  operations: operationsApi,
};

console.log(" API modules loaded:", Object.keys(API));
