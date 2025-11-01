/**
 * Chart Manager for visualizing household budget data
 * Uses Chart.js for rendering interactive charts
 */

class ChartManager {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.chart = null;
    }

    /**
     * Destroy existing chart
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    /**
     * Create a pie chart from data
     * @param {Array} data - Array of transaction objects
     */
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
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: {
                                size: 12
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ¥${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a bar chart from data
     * @param {Array} data - Array of transaction objects
     */
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
                datasets: [{
                    label: '支出額 (¥)',
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.parsed.y || 0;
                                return `¥${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `¥${value.toLocaleString()}`
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a line chart from data (by date)
     * @param {Array} data - Array of transaction objects
     */
    createLineChart(data) {
        this.destroy();

        const dailyTotals = this.aggregateByDate(data);
        const labels = Object.keys(dailyTotals).sort();
        const values = labels.map(date => dailyTotals[date]);

        this.chart = new Chart(this.ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '日別支出額 (¥)',
                    data: values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.parsed.y || 0;
                                return `支出: ¥${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `¥${value.toLocaleString()}`
                        }
                    }
                }
            }
        });
    }

    /**
     * Aggregate data by category
     * @param {Array} data - Array of transaction objects
     * @returns {Object} - Category totals
     */
    aggregateByCategory(data) {
        const totals = {};
        data.forEach(item => {
            const category = item['大項目'] || item['カテゴリ'] || item.category || '未分類';
            const amount = Math.abs(parseFloat(item['金額（円）'] || item['金額'] || item.amount || 0));
            totals[category] = (totals[category] || 0) + amount;
        });
        return totals;
    }

    /**
     * Aggregate data by date
     * @param {Array} data - Array of transaction objects
     * @returns {Object} - Daily totals
     */
    aggregateByDate(data) {
        const totals = {};
        data.forEach(item => {
            const date = item['日付'] || item.date || '';
            const dateStr = date.split(' ')[0]; // Extract date part
            const amount = Math.abs(parseFloat(item['金額（円）'] || item['金額'] || item.amount || 0));
            totals[dateStr] = (totals[dateStr] || 0) + amount;
        });
        return totals;
    }

    /**
     * Generate colors for charts
     * @param {number} count - Number of colors to generate
     * @returns {Array} - Array of color strings
     */
    generateColors(count) {
        const baseColors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
        ];

        if (count <= baseColors.length) {
            return baseColors.slice(0, count);
        }

        // Generate additional colors if needed
        const colors = [...baseColors];
        for (let i = baseColors.length; i < count; i++) {
            const hue = (i * 137.508) % 360; // Golden angle approximation
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }
        return colors;
    }

    /**
     * Get unique categories from data
     * @param {Array} data - Array of transaction objects
     * @returns {Array} - Sorted array of unique categories
     */
    static getCategories(data) {
        const categories = new Set();
        data.forEach(item => {
            const category = item['大項目'] || item.category || '未分類';
            categories.add(category);
        });
        return Array.from(categories).sort();
    }
}

// Export for use in other scripts
window.ChartManager = ChartManager;
