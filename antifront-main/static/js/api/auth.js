/**
 * Authentication API endpoints
 */

const authApi = {
  /**
   * Register new user
   * @param {Object} data - Registration data
   * @param {string} data.email - User email
   * @param {string} data.password - User password
   * @param {string} data.full_name - User full name
   * @param {boolean} data.is_admin - Is admin user
   * @returns {Promise<{success: boolean}>}
   */
  register(data) {
    return apiClient.post("/api/auth/register", data);
  },

  /**
   * Login user
   * @param {Object} data - Login credentials
   * @param {string} data.email - User email
   * @param {string} data.password - User password
   * @returns {Promise<{success: boolean}>}
   * Sets auth cookies automatically
   */
  login(data) {
    return apiClient.post("/api/auth/login", data);
  },

  /**
   * Refresh access token
   * @returns {Promise<{success: boolean}>}
   */
  refresh() {
    return apiClient.post("/api/auth/refresh", {});
  },

  /**
   * Logout user
   * @returns {Promise<{success: boolean}>}
   */
  logout() {
    return apiClient.post("/api/auth/logout", {});
  },

  /**
   * Get current user profile
   * @returns {Promise<UserProfile>}
   */
  getCurrentUser() {
    return apiClient.get("/api/users/me");
  },
};
