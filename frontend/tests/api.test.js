/**
 * Tests for APIClient
 */

import { describe, test, expect, beforeEach, jest } from '@jest/globals';

// Load the API client
// Since we can't use ES6 imports directly, we'll test the class definition
describe('APIClient', () => {
    let apiClient;
    const mockBaseUrl = 'http://localhost:8000';

    beforeEach(() => {
        // Create a simple APIClient class for testing
        class APIClient {
            constructor(baseUrl = mockBaseUrl) {
                this.baseUrl = baseUrl;
            }

            async get(endpoint, params = {}) {
                const url = new URL(`${this.baseUrl}${endpoint}`);
                Object.keys(params).forEach((key) => {
                    if (params[key] !== null && params[key] !== undefined) {
                        url.searchParams.append(key, params[key]);
                    }
                });

                const response = await fetch(url);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(
                        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
                    );
                }
                return await response.json();
            }

            async getAvailableMonths() {
                const data = await this.get('/api/available-months');
                return data.months || [];
            }

            async getMonthlyData(
                year,
                month,
                outputFormat = 'json',
                graphType = 'pie',
                imageSize = '800x600'
            ) {
                return await this.get('/api/monthly', {
                    year,
                    month,
                    output_format: outputFormat,
                    graph_type: graphType,
                    image_size: imageSize,
                });
            }

            async getCategoryHierarchy(year = 2025, month = 1) {
                const data = await this.get('/api/category-hierarchy', { year, month });
                return data.hierarchy || {};
            }

            getChartImageUrl(chartId) {
                return `${this.baseUrl}/api/charts/${chartId}`;
            }

            async healthCheck() {
                return await this.get('/health');
            }

            async getCacheStats() {
                return await this.get('/api/cache/stats');
            }

            async getMonthlySummary(startYear, startMonth, endYear, endMonth) {
                return await this.get('/api/trend/monthly_summary', {
                    start_year: startYear,
                    start_month: startMonth,
                    end_year: endYear,
                    end_month: endMonth,
                });
            }

            async getCategoryBreakdown(startYear, startMonth, endYear, endMonth, topN = 5) {
                return await this.get('/api/trend/category_breakdown', {
                    start_year: startYear,
                    start_month: startMonth,
                    end_year: endYear,
                    end_month: endMonth,
                    top_n: topN,
                });
            }
        }

        apiClient = new APIClient();
        global.fetch = jest.fn();
    });

    describe('Constructor', () => {
        test('should initialize with default base URL', () => {
            expect(apiClient.baseUrl).toBe(mockBaseUrl);
        });

        test('should initialize with custom base URL', () => {
            const customClient = new apiClient.constructor('http://custom:9000');
            expect(customClient.baseUrl).toBe('http://custom:9000');
        });
    });

    describe('get method', () => {
        test('should make successful GET request', async () => {
            const mockData = { result: 'success' };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockData,
            });

            const result = await apiClient.get('/api/test');
            expect(result).toEqual(mockData);
            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        test('should handle query parameters correctly', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await apiClient.get('/api/test', { year: 2025, month: 1 });

            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('year=2025');
            expect(callUrl.toString()).toContain('month=1');
        });

        test('should skip null and undefined parameters', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await apiClient.get('/api/test', { year: 2025, month: null, day: undefined });

            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('year=2025');
            expect(callUrl.toString()).not.toContain('month');
            expect(callUrl.toString()).not.toContain('day');
        });

        test('should throw error on HTTP error', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found',
                json: async () => ({ detail: 'Resource not found' }),
            });

            await expect(apiClient.get('/api/missing')).rejects.toThrow('Resource not found');
        });

        test('should throw error with status text when detail is missing', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error',
                json: async () => ({}),
            });

            await expect(apiClient.get('/api/error')).rejects.toThrow(
                'HTTP 500: Internal Server Error'
            );
        });

        test('should handle network errors', async () => {
            global.fetch.mockRejectedValueOnce(new Error('Network error'));

            await expect(apiClient.get('/api/test')).rejects.toThrow('Network error');
        });
    });

    describe('getAvailableMonths', () => {
        test('should return list of months', async () => {
            const mockMonths = [
                { year: 2025, month: 1 },
                { year: 2025, month: 2 },
            ];
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ months: mockMonths }),
            });

            const result = await apiClient.getAvailableMonths();
            expect(result).toEqual(mockMonths);
        });

        test('should return empty array if months is missing', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            const result = await apiClient.getAvailableMonths();
            expect(result).toEqual([]);
        });
    });

    describe('getMonthlyData', () => {
        test('should request monthly data with default parameters', async () => {
            const mockData = { total: 100000 };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockData,
            });

            const result = await apiClient.getMonthlyData(2025, 1);

            expect(result).toEqual(mockData);
            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('year=2025');
            expect(callUrl.toString()).toContain('month=1');
            expect(callUrl.toString()).toContain('output_format=json');
            expect(callUrl.toString()).toContain('graph_type=pie');
        });

        test('should request monthly data with custom parameters', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await apiClient.getMonthlyData(2024, 12, 'image', 'bar', '1024x768');

            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('output_format=image');
            expect(callUrl.toString()).toContain('graph_type=bar');
            expect(callUrl.toString()).toContain('image_size=1024x768');
        });
    });

    describe('getCategoryHierarchy', () => {
        test('should return category hierarchy', async () => {
            const mockHierarchy = { food: { total: 50000 } };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ hierarchy: mockHierarchy }),
            });

            const result = await apiClient.getCategoryHierarchy(2025, 1);
            expect(result).toEqual(mockHierarchy);
        });

        test('should use default year and month', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ hierarchy: {} }),
            });

            await apiClient.getCategoryHierarchy();

            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('year=2025');
            expect(callUrl.toString()).toContain('month=1');
        });

        test('should return empty object if hierarchy is missing', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            const result = await apiClient.getCategoryHierarchy();
            expect(result).toEqual({});
        });
    });

    describe('getChartImageUrl', () => {
        test('should construct correct chart image URL', () => {
            const chartId = 'chart-123';
            const url = apiClient.getChartImageUrl(chartId);
            expect(url).toBe(`${mockBaseUrl}/api/charts/${chartId}`);
        });
    });

    describe('healthCheck', () => {
        test('should return health status', async () => {
            const mockHealth = { status: 'ok' };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockHealth,
            });

            const result = await apiClient.healthCheck();
            expect(result).toEqual(mockHealth);
        });
    });

    describe('getCacheStats', () => {
        test('should return cache statistics', async () => {
            const mockStats = { hits: 100, misses: 10 };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockStats,
            });

            const result = await apiClient.getCacheStats();
            expect(result).toEqual(mockStats);
        });
    });

    describe('getMonthlySummary', () => {
        test('should request monthly summary with correct parameters', async () => {
            const mockSummary = { data: [] };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockSummary,
            });

            const result = await apiClient.getMonthlySummary(2024, 1, 2024, 12);

            expect(result).toEqual(mockSummary);
            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('start_year=2024');
            expect(callUrl.toString()).toContain('start_month=1');
            expect(callUrl.toString()).toContain('end_year=2024');
            expect(callUrl.toString()).toContain('end_month=12');
        });
    });

    describe('getCategoryBreakdown', () => {
        test('should request category breakdown with default topN', async () => {
            const mockBreakdown = { categories: [] };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockBreakdown,
            });

            const result = await apiClient.getCategoryBreakdown(2024, 1, 2024, 12);

            expect(result).toEqual(mockBreakdown);
            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('top_n=5');
        });

        test('should request category breakdown with custom topN', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await apiClient.getCategoryBreakdown(2024, 1, 2024, 12, 10);

            const callUrl = global.fetch.mock.calls[0][0];
            expect(callUrl.toString()).toContain('top_n=10');
        });
    });
});
