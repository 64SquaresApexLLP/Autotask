import apiService from './api';
import { API_BASE_URL } from '../config/api.js';

const BASE = '/admin/reports/ont-truck-roll';

export const ontTruckRollService = {
  async getKpiSummary() {
    return await apiService.get(`${BASE}/kpi-summary`);
  },
  async getSolutionBreakdown() {
    return await apiService.get(`${BASE}/solution-breakdown`);
  },
  async getMonthlyTrend() {
    return await apiService.get(`${BASE}/monthly-trend`);
  },
  async getServiceAreas() {
    return await apiService.get(`${BASE}/service-areas`);
  },
  async getTechnicians() {
    return await apiService.get(`${BASE}/technicians`);
  },
  async getAddresses(minCount = 1, limit = 500) {
    return await apiService.get(`${BASE}/addresses`, { min_count: minCount, limit });
  },
  async getDataQuality() {
    return await apiService.get(`${BASE}/data-quality`);
  },
  async getWeatherStats() {
    return await apiService.get(`${BASE}/weather-stats`);
  },
  async getCortexSummaries() {
    return await apiService.get(`${BASE}/cortex-summaries`);
  },
  async getRecords(filters = {}) {
    return await apiService.get(`${BASE}/records`, filters);
  },
  async getRecordDetail(ontTruckRollId) {
    return await apiService.get(`${BASE}/records/${ontTruckRollId}`);
  },

  /**
   * Trigger a server-side CSV export for the current filtered dataset.
   * All rows matching the filters are exported (not just the current page).
   * The backend enforces admin authorization and never exposes Snowflake credentials.
   */
  async exportCSV(filters = {}) {
    const token = localStorage.getItem('authToken');
    const url = new URL(`${API_BASE_URL}${BASE}/export`);

    // Forward all active filters as query params
    const filterParamMap = {
      search: 'search',
      date_from: 'date_from',
      date_to: 'date_to',
      solution: 'solution',
      service_city: 'service_city',
      service_revenue_area: 'service_revenue_area',
      technician: 'technician',
      order_status: 'order_status',
      weather_match_status: 'weather_match_status',
      location_match_type: 'location_match_type',
    };
    Object.entries(filterParamMap).forEach(([filterKey, paramKey]) => {
      const val = filters[filterKey];
      if (val) url.searchParams.append(paramKey, val);
    });

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/csv',
      },
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Export failed (HTTP ${response.status})`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    // Use filename from Content-Disposition header if available, else fallback
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    a.download = match ? match[1] : `ONT_Truck_Roll_Export_${new Date().toISOString().slice(0, 10)}.csv`;
    a.href = objectUrl;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objectUrl);
  },
};

export default ontTruckRollService;
