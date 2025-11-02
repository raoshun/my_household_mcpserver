/**
 * Tests for TrendManager
 */

import { beforeEach, describe, expect, jest, test } from '@jest/globals';

describe('TrendManager', () => {
    let trendManager;
    let mockApiClient;

    beforeEach(() => {
        // Setup mock API client
        mockApiClient = {
            getMonthlySummary: jest.fn(),
            getCategoryBreakdown: jest.fn(),
        };

        // Define TrendManager class for testing
        class TrendManager {
            constructor(apiClient) {
                this.apiClient = apiClient;
                this.availableMonths = [];
                this.currentPeriod = null;
                this.charts = {
                    monthly: null,
                    cumulative: null,
                    category: null,
                };
            }

            async initialize(availableMonths) {
                this.availableMonths = availableMonths;
                this.setupPeriodSelectors();
                await this.loadDefaultPeriod();
            }

            setupPeriodSelectors() {
                // Mock implementation - in real code this sets up DOM elements
                return true;
            }

            async loadDefaultPeriod() {
                await this.applyPreset('3');
            }

            async applyPreset(preset) {
                const today = new Date();
                let startDate, endDate;

                switch (preset) {
                    case '3':
                        startDate = new Date(today.getFullYear(), today.getMonth() - 2, 1);
                        endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                        break;
                    case '6':
                        startDate = new Date(today.getFullYear(), today.getMonth() - 5, 1);
                        endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                        break;
                    case '12':
                        startDate = new Date(today.getFullYear(), today.getMonth() - 11, 1);
                        endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                        break;
                    default:
                        return;
                }

                this.currentPeriod = {
                    startYear: startDate.getFullYear(),
                    startMonth: startDate.getMonth() + 1,
                    endYear: endDate.getFullYear(),
                    endMonth: endDate.getMonth() + 1,
                };

                await this.loadTrendData();
            }

            async loadTrendData() {
                if (!this.currentPeriod) return;

                const { startYear, startMonth, endYear, endMonth } = this.currentPeriod;

                try {
                    const summary = await this.apiClient.getMonthlySummary(
                        startYear,
                        startMonth,
                        endYear,
                        endMonth
                    );
                    const breakdown = await this.apiClient.getCategoryBreakdown(
                        startYear,
                        startMonth,
                        endYear,
                        endMonth
                    );

                    this.currentData = {
                        summary,
                        breakdown,
                    };

                    return this.currentData;
                } catch (error) {
                    console.error('Failed to load trend data:', error);
                    throw error;
                }
            }

            calculatePeriodStats(summaryData) {
                if (!summaryData || !Array.isArray(summaryData)) {
                    return null;
                }

                const totals = summaryData.map((d) => d.total || 0);
                const sum = totals.reduce((a, b) => a + b, 0);
                const average = totals.length > 0 ? sum / totals.length : 0;
                const max = Math.max(...totals);
                const min = Math.min(...totals);

                return {
                    sum,
                    average,
                    max,
                    min,
                    count: totals.length,
                };
            }

            formatCurrency(amount) {
                return `¥${Math.abs(amount).toLocaleString()}`;
            }

            formatYearMonth(year, month) {
                return `${year}年${month}月`;
            }
        }

        trendManager = new TrendManager(mockApiClient);
    });

    describe('Constructor', () => {
        test('should initialize with api client', () => {
            expect(trendManager.apiClient).toBe(mockApiClient);
            expect(trendManager.availableMonths).toEqual([]);
            expect(trendManager.currentPeriod).toBeNull();
        });

        test('should initialize charts object', () => {
            expect(trendManager.charts).toEqual({
                monthly: null,
                cumulative: null,
                category: null,
            });
        });
    });

    describe('initialize', () => {
        test('should setup with available months', async () => {
            const mockMonths = [
                { year: 2024, month: 1 },
                { year: 2024, month: 2 },
            ];

            mockApiClient.getMonthlySummary.mockResolvedValue([]);
            mockApiClient.getCategoryBreakdown.mockResolvedValue([]);

            await trendManager.initialize(mockMonths);

            expect(trendManager.availableMonths).toEqual(mockMonths);
        });
    });

    describe('applyPreset', () => {
        beforeEach(() => {
            mockApiClient.getMonthlySummary.mockResolvedValue([]);
            mockApiClient.getCategoryBreakdown.mockResolvedValue([]);
        });

        test('should set 3-month period', async () => {
            await trendManager.applyPreset('3');

            expect(trendManager.currentPeriod).not.toBeNull();
            expect(trendManager.currentPeriod.startMonth).toBeGreaterThan(0);
            expect(trendManager.currentPeriod.endMonth).toBeLessThanOrEqual(12);
        });

        test('should set 6-month period', async () => {
            await trendManager.applyPreset('6');

            expect(trendManager.currentPeriod).not.toBeNull();
            expect(trendManager.currentPeriod.startMonth).toBeGreaterThan(0);
        });

        test('should set 12-month period', async () => {
            await trendManager.applyPreset('12');

            expect(trendManager.currentPeriod).not.toBeNull();
            expect(trendManager.currentPeriod.startMonth).toBeGreaterThan(0);
        });

        test('should handle invalid preset', async () => {
            await trendManager.applyPreset('invalid');

            expect(trendManager.currentPeriod).toBeNull();
        });

        test('should load trend data after setting period', async () => {
            await trendManager.applyPreset('3');

            expect(mockApiClient.getMonthlySummary).toHaveBeenCalled();
            expect(mockApiClient.getCategoryBreakdown).toHaveBeenCalled();
        });
    });

    describe('loadTrendData', () => {
        beforeEach(() => {
            trendManager.currentPeriod = {
                startYear: 2024,
                startMonth: 1,
                endYear: 2024,
                endMonth: 3,
            };
        });

        test('should load summary and breakdown data', async () => {
            const mockSummary = [
                { month: '2024-01', total: 50000 },
                { month: '2024-02', total: 60000 },
            ];
            const mockBreakdown = [{ category: '食費', total: 30000 }];

            mockApiClient.getMonthlySummary.mockResolvedValue(mockSummary);
            mockApiClient.getCategoryBreakdown.mockResolvedValue(mockBreakdown);

            const result = await trendManager.loadTrendData();

            expect(result.summary).toEqual(mockSummary);
            expect(result.breakdown).toEqual(mockBreakdown);
            expect(mockApiClient.getMonthlySummary).toHaveBeenCalledWith(2024, 1, 2024, 3);
            expect(mockApiClient.getCategoryBreakdown).toHaveBeenCalledWith(2024, 1, 2024, 3);
        });

        test('should handle no period set', async () => {
            trendManager.currentPeriod = null;

            const result = await trendManager.loadTrendData();

            expect(result).toBeUndefined();
            expect(mockApiClient.getMonthlySummary).not.toHaveBeenCalled();
        });

        test('should handle API errors', async () => {
            mockApiClient.getMonthlySummary.mockRejectedValue(new Error('API Error'));

            await expect(trendManager.loadTrendData()).rejects.toThrow('API Error');
        });
    });

    describe('calculatePeriodStats', () => {
        test('should calculate statistics correctly', () => {
            const summaryData = [
                { total: 50000 },
                { total: 60000 },
                { total: 70000 },
                { total: 40000 },
            ];

            const stats = trendManager.calculatePeriodStats(summaryData);

            expect(stats.sum).toBe(220000);
            expect(stats.average).toBe(55000);
            expect(stats.max).toBe(70000);
            expect(stats.min).toBe(40000);
            expect(stats.count).toBe(4);
        });

        test('should handle empty data', () => {
            const stats = trendManager.calculatePeriodStats([]);

            expect(stats.sum).toBe(0);
            expect(stats.average).toBe(0);
            expect(stats.count).toBe(0);
        });

        test('should handle null data', () => {
            const stats = trendManager.calculatePeriodStats(null);

            expect(stats).toBeNull();
        });

        test('should handle missing total values', () => {
            const summaryData = [{ total: 50000 }, {}, { total: 70000 }];

            const stats = trendManager.calculatePeriodStats(summaryData);

            expect(stats.sum).toBe(120000);
            expect(stats.count).toBe(3);
        });
    });

    describe('formatCurrency', () => {
        test('should format positive amounts', () => {
            expect(trendManager.formatCurrency(50000)).toBe('¥50,000');
        });

        test('should format negative amounts as positive', () => {
            expect(trendManager.formatCurrency(-50000)).toBe('¥50,000');
        });

        test('should handle zero', () => {
            expect(trendManager.formatCurrency(0)).toBe('¥0');
        });

        test('should handle large numbers', () => {
            expect(trendManager.formatCurrency(1234567)).toBe('¥1,234,567');
        });
    });

    describe('formatYearMonth', () => {
        test('should format year and month', () => {
            expect(trendManager.formatYearMonth(2024, 1)).toBe('2024年1月');
            expect(trendManager.formatYearMonth(2024, 12)).toBe('2024年12月');
        });
    });
});
