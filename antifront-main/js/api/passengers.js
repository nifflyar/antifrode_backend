/**
 * Passengers API endpoints
 */

const passengersApi = {
  /**
   * Get list of passengers with filters
   * @param {Object} filters - Filtering options
   * @param {string} filters.riskBand - Optional: low | medium | high | critical
   * @param {string} filters.search - Optional: search by FIO or IIN
   * @param {number} filters.limit - Default: 50
   * @param {number} filters.offset - Default: 0
   * @returns {Promise<PassengerListResponse>}
   */
  getList(filters = {}) {
    const params = new URLSearchParams();
    if (filters.riskBand) params.append("risk_band", filters.riskBand);
    if (filters.search) params.append("search", filters.search);
    if (filters.limit) params.append("limit", filters.limit);
    if (filters.offset) params.append("offset", filters.offset);

    const query = params.toString();
    return apiClient.get(`/api/passengers${query ? "?" + query : ""}`);
  },

  /**
   * Get passenger profile with detailed info
   * @param {string} passengerId - Passenger ID
   * @returns {Promise<PassengerProfileResponse>}
   */
  getProfile(passengerId) {
    return apiClient.get(`/api/passengers/${passengerId}`);
  },

  /**
   * Get passenger transactions
   * @param {string} passengerId - Passenger ID
   * @param {Object} filters - Optional filters
   * @returns {Promise<PassengerTransactionsResponse>}
   */
  getTransactions(passengerId, filters = {}) {
    const params = new URLSearchParams();
    if (filters.limit) params.append("limit", filters.limit);
    if (filters.offset) params.append("offset", filters.offset);

    const query = params.toString();
    return apiClient.get(`/api/passengers/${passengerId}/transactions${query ? "?" + query : ""}`);
  },

  /**
   * Override passenger risk score
   * @param {string} passengerId - Passenger ID
   * @param {Object} data - Override data
   * @param {string} data.new_risk_band - NEW RISK BAND (low|medium|high|critical)
   * @param {string} data.reason - Reason for override
   * @returns {Promise<void>}
   */
  overrideRisk(passengerId, data) {
    return apiClient.post(`/api/passengers/${passengerId}/override`, data);
  },
};
