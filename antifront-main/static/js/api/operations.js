/**
 * Operations API endpoints
 */

const operationsApi = {
  /**
   * Get list of suspicious operations
   * @param {Object} filters - Filtering options
   * @param {string} filters.train_no - Optional: filter by train number
   * @param {string} filters.terminal - Optional: filter by terminal
   * @param {string} filters.cashdesk - Optional: filter by cashdesk
   * @param {string} filters.channel - Optional: filter by channel
   * @param {number} filters.limit - Default: 100
   * @param {number} filters.offset - Default: 0
   * @returns {Promise<OperationsListResponse>}
   */
  getList(filters = {}) {
    const params = new URLSearchParams();
    if (filters.train_no) params.append("train_no", filters.train_no);
    if (filters.terminal) params.append("terminal", filters.terminal);
    if (filters.cashdesk) params.append("cashdesk", filters.cashdesk);
    if (filters.channel) params.append("channel", filters.channel);
    if (filters.limit) params.append("limit", filters.limit);
    if (filters.offset) params.append("offset", filters.offset);

    const query = params.toString();
    return apiClient.get(`/api/operations/suspicious${query ? "?" + query : ""}`);
  },

  /**
   * Get operation details
   * @param {string} operationId - Operation ID
   * @returns {Promise<OperationDetailResponse>}
   */
  getDetails(operationId) {
    return apiClient.get(`/api/operations/${operationId}`);
  },
};
