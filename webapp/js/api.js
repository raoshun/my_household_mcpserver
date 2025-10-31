/**
 * API Client for Household Budget Server
 * Handles all HTTP requests to the FastAPI backend
 */

const API_BASE_URL = 'http://localhost:8000';

class APIClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    /**
     * Make a GET request to the API
     * @param {string} endpoint - API endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} - Response data
     */
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });

        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Get available months
     * @returns {Promise<Array>} - List of available year-month combinations
     */
    async getAvailableMonths() {
        const data = await this.get('/api/available-months');
        return data.months || [];
    }

    /**
     * Get monthly household data
     * @param {number} year - Year
     * @param {number} month - Month (1-12)
     * @param {string} outputFormat - Output format ('json' or 'image')
     * @param {string} graphType - Graph type ('pie', 'bar', 'line', 'area')
     * @param {string} imageSize - Image size (e.g., '800x600')
     * @returns {Promise<Object>} - Monthly data
     */
    async getMonthlyData(year, month, outputFormat = 'json', graphType = 'pie', imageSize = '800x600') {
        return await this.get('/api/monthly', {
            year,
            month,
            output_format: outputFormat,
            graph_type: graphType,
            image_size: imageSize
        });
    }

    /**
     * Get category hierarchy
     * @param {number} year - Year
     * @param {number} month - Month
     * @returns {Promise<Object>} - Category hierarchy
     */
    async getCategoryHierarchy(year = 2025, month = 1) {
        const data = await this.get('/api/category-hierarchy', { year, month });
        return data.hierarchy || {};
    }

    /**
     * Get chart image by ID
     * @param {string} chartId - Chart ID
     * @returns {string} - Image URL
     */
    getChartImageUrl(chartId) {
        return `${this.baseUrl}/api/charts/${chartId}`;
    }

    /**
     * Health check
     * @returns {Promise<Object>} - Health status
     */
    async healthCheck() {
        return await this.get('/health');
    }

    /**
     * Get cache statistics
     * @returns {Promise<Object>} - Cache statistics
     */
    async getCacheStats() {
        return await this.get('/api/cache/stats');
    }
}

// Export for use in other scripts
window.APIClient = APIClient;
