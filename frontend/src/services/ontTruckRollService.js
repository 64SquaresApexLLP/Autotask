import apiService from './api';

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
};

export default ontTruckRollService;
