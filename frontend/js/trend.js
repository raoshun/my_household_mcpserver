/**
 * Trend Analysis Manager
 * Handles period selection, data loading, and trend visualization
 */

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

    /**
     * Initialize trend manager
     */
    async initialize(availableMonths) {
        this.availableMonths = availableMonths;
        this.setupPeriodSelectors();
        this.setupEventListeners();
        await this.loadDefaultPeriod();
    }

    /**
     * Setup period selector dropdowns
     */
    setupPeriodSelectors() {
        const startYearSelect = document.getElementById('trend-start-year');
        const startMonthSelect = document.getElementById('trend-start-month');
        const endYearSelect = document.getElementById('trend-end-year');
        const endMonthSelect = document.getElementById('trend-end-month');

        if (!startYearSelect || !endYearSelect) return;

        // Get unique years
        const years = [...new Set(this.availableMonths.map((m) => m.year))].sort((a, b) => b - a);

        // Populate year selects
        years.forEach((year) => {
            startYearSelect.add(new Option(`${year}年`, year));
            endYearSelect.add(new Option(`${year}年`, year));
        });

        // Populate month selects (1-12)
        for (let month = 1; month <= 12; month++) {
            startMonthSelect.add(new Option(`${month}月`, month));
            endMonthSelect.add(new Option(`${month}月`, month));
        }
    }

    /**
     * Setup event listeners for period selection
     */
    setupEventListeners() {
        // Preset buttons
        const presetButtons = document.querySelectorAll('.preset-btn');
        presetButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const preset = e.target.dataset.preset;
                this.applyPreset(preset);
            });
        });

        // Apply custom period button
        const applyButton = document.getElementById('apply-trend-period');
        if (applyButton) {
            applyButton.addEventListener('click', () => {
                this.applyCustomPeriod();
            });
        }

        // Trend tab navigation
        const trendTabButtons = document.querySelectorAll('.trend-tab-btn');
        trendTabButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const trendType = e.target.dataset.trend;
                this.switchTrendTab(trendType);
            });
        });
    }

    /**
     * Load default period (last 3 months)
     */
    async loadDefaultPeriod() {
        await this.applyPreset('3');
    }

    /**
     * Apply preset period
     */
    async applyPreset(preset) {
        // Update active button
        document.querySelectorAll('.preset-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.preset === preset);
        });

        if (this.availableMonths.length === 0) {
            this.showError('利用可能な月がありません');
            return;
        }

        // Sort months
        const sortedMonths = [...this.availableMonths].sort((a, b) => {
            if (a.year !== b.year) return b.year - a.year;
            return b.month - a.month;
        });

        const latestMonth = sortedMonths[0];
        let startYear, startMonth;

        if (preset === 'all') {
            // All available data
            const oldestMonth = sortedMonths[sortedMonths.length - 1];
            startYear = oldestMonth.year;
            startMonth = oldestMonth.month;
        } else {
            // Calculate start date based on preset
            const monthsBack = parseInt(preset);
            const endDate = new Date(latestMonth.year, latestMonth.month - 1, 1);
            const startDate = new Date(endDate);
            startDate.setMonth(startDate.getMonth() - monthsBack + 1);

            startYear = startDate.getFullYear();
            startMonth = startDate.getMonth() + 1;
        }

        // Update selectors
        this.updatePeriodSelectors(startYear, startMonth, latestMonth.year, latestMonth.month);

        // Load data
        await this.loadTrendData(startYear, startMonth, latestMonth.year, latestMonth.month);
    }

    /**
     * Apply custom period from selectors
     */
    async applyCustomPeriod() {
        const startYear = parseInt(document.getElementById('trend-start-year').value);
        const startMonth = parseInt(document.getElementById('trend-start-month').value);
        const endYear = parseInt(document.getElementById('trend-end-year').value);
        const endMonth = parseInt(document.getElementById('trend-end-month').value);

        // Validate
        const startDate = new Date(startYear, startMonth - 1, 1);
        const endDate = new Date(endYear, endMonth - 1, 1);

        if (startDate > endDate) {
            this.showError('開始日は終了日より前である必要があります');
            return;
        }

        // Deactivate preset buttons
        document.querySelectorAll('.preset-btn').forEach((btn) => {
            btn.classList.remove('active');
        });

        await this.loadTrendData(startYear, startMonth, endYear, endMonth);
    }

    /**
     * Update period selectors
     */
    updatePeriodSelectors(startYear, startMonth, endYear, endMonth) {
        document.getElementById('trend-start-year').value = startYear;
        document.getElementById('trend-start-month').value = startMonth;
        document.getElementById('trend-end-year').value = endYear;
        document.getElementById('trend-end-month').value = endMonth;
    }

    /**
     * Load trend data and update all charts
     */
    async loadTrendData(startYear, startMonth, endYear, endMonth) {
        try {
            this.showLoading(true);
            this.hideError();

            // Store current period
            this.currentPeriod = { startYear, startMonth, endYear, endMonth };

            // Load monthly summary
            const summaryResult = await this.apiClient.getMonthlySummary(
                startYear,
                startMonth,
                endYear,
                endMonth
            );

            // Load category breakdown
            const categoryResult = await this.apiClient.getCategoryBreakdown(
                startYear,
                startMonth,
                endYear,
                endMonth,
                5
            );

            if (summaryResult.success && categoryResult.success) {
                this.updateMonthlyTrendChart(summaryResult.data);
                this.updateCumulativeTrendChart(summaryResult.data);
                this.updateCategoryTrendChart(categoryResult);
            } else {
                throw new Error('データの読み込みに失敗しました');
            }
        } catch (error) {
            console.error('Error loading trend data:', error);
            this.showError('トレンドデータの読み込みに失敗しました: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Update monthly trend chart (income, expense, balance)
     */
    updateMonthlyTrendChart(data) {
        const ctx = document.getElementById('monthly-trend-chart');
        if (!ctx) return;

        const labels = data.map((d) => d.year_month);
        const income = data.map((d) => d.income);
        const expense = data.map((d) => d.expense);
        const balance = data.map((d) => d.balance);

        // Destroy previous chart
        if (this.charts.monthly) {
            this.charts.monthly.destroy();
        }

        this.charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '収入',
                        data: income,
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3,
                        fill: true,
                    },
                    {
                        label: '支出',
                        data: expense,
                        borderColor: 'rgb(239, 68, 68)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.3,
                        fill: true,
                    },
                    {
                        label: '収支差額',
                        data: balance,
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.3,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '¥' + context.parsed.y.toLocaleString();
                                return label;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return '¥' + value.toLocaleString();
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * Update cumulative trend chart
     */
    updateCumulativeTrendChart(data) {
        const ctx = document.getElementById('cumulative-trend-chart');
        if (!ctx) return;

        const labels = data.map((d) => d.year_month);
        const cumulative = data.map((d) => d.cumulative_balance);

        // Destroy previous chart
        if (this.charts.cumulative) {
            this.charts.cumulative.destroy();
        }

        this.charts.cumulative = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '累積収支',
                        data: cumulative,
                        borderColor: 'rgb(139, 92, 246)',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.3,
                        fill: true,
                        borderWidth: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return '累積収支: ¥' + context.parsed.y.toLocaleString();
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function (value) {
                                return '¥' + value.toLocaleString();
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * Update category trend chart (stacked bar)
     */
    updateCategoryTrendChart(result) {
        const ctx = document.getElementById('category-trend-chart');
        if (!ctx) return;

        const labels = result.months;
        const categories = result.categories;
        const data = result.data;

        // Destroy previous chart
        if (this.charts.category) {
            this.charts.category.destroy();
        }

        // Generate colors for categories
        const colors = [
            'rgb(239, 68, 68)',
            'rgb(249, 115, 22)',
            'rgb(245, 158, 11)',
            'rgb(34, 197, 94)',
            'rgb(59, 130, 246)',
            'rgb(168, 85, 247)',
            'rgb(236, 72, 153)',
        ];

        const datasets = categories.map((category, index) => ({
            label: category,
            data: data.map((d) => d[category] || 0),
            backgroundColor: colors[index % colors.length],
            borderColor: colors[index % colors.length],
            borderWidth: 1,
        }));

        this.charts.category = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '¥' + context.parsed.y.toLocaleString();
                                return label;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        stacked: true,
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return '¥' + value.toLocaleString();
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * Switch between trend tabs
     */
    switchTrendTab(trendType) {
        // Update button states
        document.querySelectorAll('.trend-tab-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.trend === trendType);
        });

        // Update chart containers
        document.querySelectorAll('.trend-chart-container').forEach((container) => {
            container.classList.remove('active');
        });

        const activeContainer = document.getElementById(`${trendType}-trend`);
        if (activeContainer) {
            activeContainer.classList.add('active');
        }
    }

    /**
     * Show loading indicator
     */
    showLoading(show) {
        const loadingIndicator = document.getElementById('trend-loading');
        if (loadingIndicator) {
            loadingIndicator.classList.toggle('hidden', !show);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorDiv = document.getElementById('trend-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
    }

    /**
     * Hide error message
     */
    hideError() {
        const errorDiv = document.getElementById('trend-error');
        if (errorDiv) {
            errorDiv.classList.add('hidden');
        }
    }
}

// Export for use in main.js
window.TrendManager = TrendManager;
