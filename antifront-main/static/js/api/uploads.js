/**
 * Uploads API endpoints for Excel file uploads and status tracking
 */

const uploadsApi = {
  /**
   * Upload an Excel file for ETL processing
   * @param {File} file - Excel file to upload (.xlsx)
   * @returns {Promise<UploadResponse>} Response with upload ID and status
   */
  async uploadExcel(file) {
    if (!file.name.endsWith('.xlsx')) {
      throw new Error('Только файлы .xlsx поддерживаются');
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/uploads/excel`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  },

  /**
   * Get status of an upload by ID
   * @param {string|number} uploadId - The upload ID to check
   * @returns {Promise<UploadResponse>} Upload status and details
   */
  getUploadStatus(uploadId) {
    return apiClient.get(`/api/uploads/${uploadId}`);
  },

  /**
   * List all uploads with pagination
   * @param {Object} options - Pagination options
   * @param {number} options.limit - Max items per page (default: 20)
   * @param {number} options.offset - Pagination offset (default: 0)
   * @returns {Promise<UploadListResponse>} List of uploads
   */
  listUploads(options = {}) {
    const { limit = 20, offset = 0 } = options;
    return apiClient.get(`/api/uploads?limit=${limit}&offset=${offset}`);
  }
};
