/**
 * Base HTTP client for all API requests
 * Handles authentication, error handling, and request/response formatting
 */

// Detect API URL from browser location or fallback to localhost
const getApiBaseUrl = () => {
  // If we have window object, use current origin (for same-origin requests)
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  // Fallback for non-browser environments
  return "http://localhost:8000";
};

const API_BASE_URL = getApiBaseUrl();


class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic request method with error handling
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      credentials: "include", // Include cookies for JWT auth
      ...options,
    };

    try {
      const response = await fetch(url, config);

      // Handle authentication errors
      if (response.status === 401) {
        this.handleUnauthorized();
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}`,
          response.status,
          errorData
        );
      }

      return response.status === 204 ? null : await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  /**
   * GET request
   */
  get(endpoint, options = {}) {
    return this.request(endpoint, {
      method: "GET",
      ...options,
    });
  }

  /**
   * POST request
   */
  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
      ...options,
    });
  }

  /**
   * PUT request
   */
  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
      ...options,
    });
  }

  /**
   * DELETE request
   */
  delete(endpoint, options = {}) {
    return this.request(endpoint, {
      method: "DELETE",
      ...options,
    });
  }

  /**
   * Handle unauthorized responses (token expired, etc)
   */
  handleUnauthorized() {
    // Clear auth state and redirect to login
    localStorage.removeItem("authToken");
    window.location.href = "/login";
  }
}

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

// Export singleton instance
const apiClient = new ApiClient();
