/**
 * Tests for ChartManager
 */

import { describe, test, expect, beforeEach, jest } from '@jest/globals';

// Use global Chart from setup.js
const Chart = global.Chart;

describe('ChartManager', () => {
    let chartManager;
    let mockCanvas;

    beforeEach(() => {
        // Setup DOM
        document.body.innerHTML = '<canvas id="test-chart"></canvas>';
        mockCanvas = document.getElementById('test-chart');

        // Define ChartManager class for testing
        class ChartManager {
            constructor(canvasId) {
                this.canvas = document.getElementById(canvasId);
                this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
                this.chart = null;
            }

            destroy() {
                if (this.chart) {
                    this.chart.destroy();
                    this.chart = null;
                }
            }

            aggregateByCategory(data) {
                const totals = {};
                data.forEach((item) => {
                    const category = item.category || 'その他';
                    totals[category] = (totals[category] || 0) + Math.abs(item.amount || 0);
                });
                return totals;
            }

            generateColors(count) {
                const colors = [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40',
                    '#FF6384',
                    '#C9CBCF',
                ];
                return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
            }

            createPieChart(data) {
                this.destroy();

                const categoryTotals = this.aggregateByCategory(data);
                const labels = Object.keys(categoryTotals);
                const values = Object.values(categoryTotals);
                const colors = this.generateColors(labels.length);

                this.chart = new Chart(this.ctx, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                data: values,
                                backgroundColor: colors,
                                borderWidth: 2,
                                borderColor: '#ffffff',
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'right',
                            },
                        },
                    },
                });
            }

            createBarChart(data) {
                this.destroy();

                const categoryTotals = this.aggregateByCategory(data);
                const labels = Object.keys(categoryTotals);
                const values = Object.values(categoryTotals);
                const colors = this.generateColors(labels.length);

                this.chart = new Chart(this.ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: '支出額 (¥)',
                                data: values,
                                backgroundColor: colors,
                                borderWidth: 2,
                                borderColor: '#ffffff',
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                    },
                });
            }

            createLineChart(monthlyData) {
                this.destroy();

                const labels = monthlyData.map((d) => d.month);
                const values = monthlyData.map((d) => d.total);

                this.chart = new Chart(this.ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: '月次支出',
                                data: values,
                                borderColor: '#36A2EB',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                tension: 0.4,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                    },
                });
            }
        }

        chartManager = new ChartManager('test-chart');
    });

    describe('Constructor', () => {
        test('should initialize with valid canvas', () => {
            expect(chartManager.canvas).toBe(mockCanvas);
            expect(chartManager.ctx).not.toBeNull();
            expect(chartManager.chart).toBeNull();
        });

        test('should handle missing canvas', () => {
            const invalidManager = new chartManager.constructor('non-existent');
            expect(invalidManager.canvas).toBeNull();
            expect(invalidManager.ctx).toBeNull();
        });
    });

    describe('destroy', () => {
        test('should destroy existing chart', () => {
            chartManager.chart = new Chart(chartManager.ctx, {
                type: 'pie',
                data: { labels: [], datasets: [] },
            });

            chartManager.destroy();
            expect(chartManager.chart).toBeNull();
        });

        test('should do nothing if no chart exists', () => {
            expect(() => chartManager.destroy()).not.toThrow();
        });
    });

    describe('aggregateByCategory', () => {
        test('should aggregate data by category', () => {
            const data = [
                { category: '食費', amount: -5000 },
                { category: '食費', amount: -3000 },
                { category: '交通費', amount: -2000 },
            ];

            const result = chartManager.aggregateByCategory(data);
            expect(result).toEqual({
                食費: 8000,
                交通費: 2000,
            });
        });

        test('should handle missing category', () => {
            const data = [{ amount: -1000 }, { category: '食費', amount: -2000 }];

            const result = chartManager.aggregateByCategory(data);
            expect(result).toEqual({
                その他: 1000,
                食費: 2000,
            });
        });

        test('should handle missing amount', () => {
            const data = [{ category: '食費' }, { category: '交通費', amount: -1000 }];

            const result = chartManager.aggregateByCategory(data);
            expect(result).toEqual({
                食費: 0,
                交通費: 1000,
            });
        });

        test('should handle empty data', () => {
            const result = chartManager.aggregateByCategory([]);
            expect(result).toEqual({});
        });
    });

    describe('generateColors', () => {
        test('should generate correct number of colors', () => {
            const colors = chartManager.generateColors(5);
            expect(colors).toHaveLength(5);
        });

        test('should cycle colors for large counts', () => {
            const colors = chartManager.generateColors(10);
            expect(colors).toHaveLength(10);
            // Should repeat colors after 8
            expect(colors[0]).toBe(colors[8]);
        });

        test('should handle zero count', () => {
            const colors = chartManager.generateColors(0);
            expect(colors).toHaveLength(0);
        });
    });

    describe('createPieChart', () => {
        test('should create pie chart with valid data', () => {
            const data = [
                { category: '食費', amount: -5000 },
                { category: '交通費', amount: -3000 },
            ];

            chartManager.createPieChart(data);

            expect(chartManager.chart).not.toBeNull();
            expect(chartManager.chart.type).toBe('pie');
            expect(chartManager.chart.data.labels).toEqual(['食費', '交通費']);
            expect(chartManager.chart.data.datasets[0].data).toEqual([5000, 3000]);
        });

        test('should destroy existing chart before creating new one', () => {
            chartManager.chart = new Chart(chartManager.ctx, {
                type: 'bar',
                data: { labels: [], datasets: [] },
            });
            const destroySpy = jest.spyOn(chartManager, 'destroy');

            chartManager.createPieChart([{ category: '食費', amount: -1000 }]);

            expect(destroySpy).toHaveBeenCalled();
        });

        test('should handle empty data', () => {
            chartManager.createPieChart([]);

            expect(chartManager.chart).not.toBeNull();
            expect(chartManager.chart.data.labels).toEqual([]);
            expect(chartManager.chart.data.datasets[0].data).toEqual([]);
        });
    });

    describe('createBarChart', () => {
        test('should create bar chart with valid data', () => {
            const data = [
                { category: '食費', amount: -5000 },
                { category: '交通費', amount: -3000 },
            ];

            chartManager.createBarChart(data);

            expect(chartManager.chart).not.toBeNull();
            expect(chartManager.chart.type).toBe('bar');
            expect(chartManager.chart.data.labels).toEqual(['食費', '交通費']);
            expect(chartManager.chart.data.datasets[0].data).toEqual([5000, 3000]);
            expect(chartManager.chart.data.datasets[0].label).toBe('支出額 (¥)');
        });

        test('should destroy existing chart before creating new one', () => {
            const destroySpy = jest.spyOn(chartManager, 'destroy');

            chartManager.createBarChart([{ category: '食費', amount: -1000 }]);

            expect(destroySpy).toHaveBeenCalled();
        });
    });

    describe('createLineChart', () => {
        test('should create line chart with monthly data', () => {
            const monthlyData = [
                { month: '2024-01', total: 50000 },
                { month: '2024-02', total: 60000 },
                { month: '2024-03', total: 55000 },
            ];

            chartManager.createLineChart(monthlyData);

            expect(chartManager.chart).not.toBeNull();
            expect(chartManager.chart.type).toBe('line');
            expect(chartManager.chart.data.labels).toEqual(['2024-01', '2024-02', '2024-03']);
            expect(chartManager.chart.data.datasets[0].data).toEqual([50000, 60000, 55000]);
        });

        test('should destroy existing chart before creating new one', () => {
            const destroySpy = jest.spyOn(chartManager, 'destroy');

            chartManager.createLineChart([{ month: '2024-01', total: 50000 }]);

            expect(destroySpy).toHaveBeenCalled();
        });

        test('should handle empty data', () => {
            chartManager.createLineChart([]);

            expect(chartManager.chart).not.toBeNull();
            expect(chartManager.chart.data.labels).toEqual([]);
            expect(chartManager.chart.data.datasets[0].data).toEqual([]);
        });
    });
});
