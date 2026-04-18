/**
 * Dashboard API endpoints
 */

const dashboardApi = {
  /**
   * Get dashboard summary (metrics)
   * @returns {Promise<DashboardSummaryResponse>}
   */
  getSummary() {
    return apiClient.get("/api/dashboard/summary");
  },

  /**
   * Get risk trend data
   * @param {Object} filters - Optional filters
   * @param {string} filters.dateFrom - Start date
   * @param {string} filters.dateTo - End date
   * @returns {Promise<RiskTrendResponse>}
   */
  getRiskTrend(filters = {}) {
    const params = new URLSearchParams();
    if (filters.dateFrom) params.append("date_from", filters.dateFrom);
    if (filters.dateTo) params.append("date_to", filters.dateTo);

    const query = params.toString();
    return apiClient.get(`/api/dashboard/risk-trend${query ? "?" + query : ""}`);
  },

  /**
   * Get risk concentration by dimension
   * @param {string} dimensionType - CHANNEL | AGGREGATOR | TERMINAL | CASHDESK
   * @returns {Promise<RiskConcentrationResponse>}
   */
  getRiskConcentration(dimensionType) {
    return apiClient.get(`/api/dashboard/risk-concentration?dimension_type=${dimensionType}`);
  },
};
