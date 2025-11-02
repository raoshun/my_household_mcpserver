/**
 * Main Application Logic
 * Coordinates API calls, chart rendering, and UI updates
 */

// Global state
let apiClient;
let chartManager;
let trendManager;
let currentData = [];
let availableMonths = [];

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Household Budget Analyzer...');

    // Initialize API client and chart manager
    apiClient = new APIClient();
    chartManager = new ChartManager('main-chart');
    trendManager = new TrendManager(apiClient);

    // Set up event listeners
    setupEventListeners();
    setupTabNavigation();

    // Load available months
    await loadAvailableMonths();

    // Initialize trend manager with available months
    await trendManager.initialize(availableMonths);

    // Perform health check
    await performHealthCheck();

    console.log('Application initialized successfully');
});

/**
 * Setup tab navigation between Monthly and Trend views
 */
function setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');

    tabButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Update button states
            tabButtons.forEach((btn) => btn.classList.remove('active'));
            button.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach((content) => {
                content.classList.remove('active');
            });

            const activeTab = document.getElementById(`${tabName}-tab`);
            if (activeTab) {
                activeTab.classList.add('active');
            }
        });
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    const loadBtn = document.getElementById('load-data-btn');
    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const graphTypeSelect = document.getElementById('graph-type-select');
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');

    if (loadBtn) {
        loadBtn.addEventListener('click', handleLoadData);
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterTable);
    }

    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterTable);
    }

    if (graphTypeSelect) {
        graphTypeSelect.addEventListener('change', () => {
            if (currentData.length > 0) {
                updateChart(currentData);
            }
        });
    }

    // Auto-select current year/month when changed
    if (yearSelect && monthSelect) {
        yearSelect.addEventListener('change', updateMonthOptions);
    }
}

/**
 * Load available months from API
 */
async function loadAvailableMonths() {
    try {
        showLoading(true);
        availableMonths = await apiClient.getAvailableMonths();
        console.log('Available months:', availableMonths);

        populateYearMonthSelects();
        hideError();
    } catch (error) {
        console.error('Error loading available months:', error);
        showError('利用可能な月の読み込みに失敗しました: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Populate year and month select dropdowns
 */
function populateYearMonthSelects() {
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');

    if (!yearSelect || !monthSelect) return;

    // Get unique years
    const years = [...new Set(availableMonths.map((m) => m.year))].sort((a, b) => b - a);

    // Populate year select
    yearSelect.innerHTML = years
        .map((year) => `<option value="${year}">${year}年</option>`)
        .join('');

    // Set default to latest year
    if (years.length > 0) {
        yearSelect.value = years[0];
        updateMonthOptions();
    }
}

/**
 * Update month options based on selected year
 */
function updateMonthOptions() {
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');

    if (!yearSelect || !monthSelect) return;

    const selectedYear = parseInt(yearSelect.value);
    const months = availableMonths
        .filter((m) => m.year === selectedYear)
        .map((m) => m.month)
        .sort((a, b) => b - a);

    monthSelect.innerHTML = months
        .map((month) => `<option value="${month}">${month}月</option>`)
        .join('');
}

/**
 * Handle load data button click
 */
async function handleLoadData() {
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');

    if (!yearSelect || !monthSelect) return;

    const year = parseInt(yearSelect.value);
    const month = parseInt(monthSelect.value);

    await loadMonthlyData(year, month);
}

/**
 * Load monthly data from API
 */
async function loadMonthlyData(year, month) {
    try {
        showLoading(true);
        hideError();

        console.log(`Loading data for ${year}/${month}...`);
        const result = await apiClient.getMonthlyData(year, month, 'json');

        if (!result.success) {
            throw new Error(result.error || 'データの読み込みに失敗しました');
        }

        currentData = result.data || [];
        console.log(`Loaded ${currentData.length} transactions`);

        // Update UI
        updateSummaryStats(currentData);
        updateChart(currentData);
        updateTable(currentData);
        updateCategoryFilter(currentData);

        hideError();
    } catch (error) {
        console.error('Error loading monthly data:', error);
        showError('データの読み込みに失敗しました: ' + error.message);
        currentData = [];
    } finally {
        showLoading(false);
    }
}

/**
 * Update summary statistics
 */
function updateSummaryStats(data) {
    const totalExpense = data.reduce((sum, item) => {
        const amount = Math.abs(parseFloat(item['金額（円）'] || item['金額'] || item.amount || 0));
        return sum + amount;
    }, 0);

    const maxExpense = Math.max(
        ...data.map((item) =>
            Math.abs(parseFloat(item['金額（円）'] || item['金額'] || item.amount || 0))
        ),
        0
    );

    const avgExpense = data.length > 0 ? totalExpense / data.length : 0;

    document.getElementById('total-expense').textContent = `¥${totalExpense.toLocaleString()}`;
    document.getElementById('transaction-count').textContent = `${data.length}件`;
    document.getElementById('average-expense').textContent =
        `¥${Math.round(avgExpense).toLocaleString()}`;
    document.getElementById('max-expense').textContent = `¥${maxExpense.toLocaleString()}`;
}

/**
 * Update chart based on selected graph type
 */
function updateChart(data) {
    const graphType = document.getElementById('graph-type-select').value;

    switch (graphType) {
        case 'pie':
            chartManager.createPieChart(data);
            break;
        case 'bar':
            chartManager.createBarChart(data);
            break;
        case 'line':
        case 'area':
            chartManager.createLineChart(data);
            break;
        default:
            chartManager.createPieChart(data);
    }
}

/**
 * Update data table
 */
function updateTable(data) {
    const tbody = document.getElementById('data-table-body');
    if (!tbody) return;

    tbody.innerHTML = data
        .map((item) => {
            const date = item['日付'] || item.date || '';
            const description = item['内容'] || item.description || '';
            const category = item['大項目'] || item.category || '未分類';
            const amount = Math.abs(
                parseFloat(item['金額（円）'] || item['金額'] || item.amount || 0)
            );

            return `
            <tr>
                <td>${escapeHtml(date)}</td>
                <td>${escapeHtml(description)}</td>
                <td>${escapeHtml(category)}</td>
                <td>¥${amount.toLocaleString()}</td>
            </tr>
        `;
        })
        .join('');
}

/**
 * Update category filter dropdown
 */
function updateCategoryFilter(data) {
    const categoryFilter = document.getElementById('category-filter');
    if (!categoryFilter) return;

    const categories = ChartManager.getCategories(data);

    categoryFilter.innerHTML =
        '<option value="">すべてのカテゴリ</option>' +
        categories
            .map((cat) => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`)
            .join('');
}

/**
 * Filter table based on search and category
 */
function filterTable() {
    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const tbody = document.getElementById('data-table-body');

    if (!searchInput || !categoryFilter || !tbody) return;

    const searchTerm = searchInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value;

    const rows = tbody.getElementsByTagName('tr');

    Array.from(rows).forEach((row) => {
        const cells = row.getElementsByTagName('td');
        if (cells.length === 0) return;

        const date = cells[0].textContent.toLowerCase();
        const description = cells[1].textContent.toLowerCase();
        const category = cells[2].textContent;

        const matchesSearch =
            !searchTerm || date.includes(searchTerm) || description.includes(searchTerm);

        const matchesCategory = !selectedCategory || category === selectedCategory;

        row.style.display = matchesSearch && matchesCategory ? '' : 'none';
    });
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.classList.toggle('hidden', !show);
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
    }
}

/**
 * Hide error message
 */
function hideError() {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.classList.add('hidden');
    }
}

/**
 * Perform health check
 */
async function performHealthCheck() {
    try {
        const health = await apiClient.healthCheck();
        console.log('Server health:', health);
    } catch (error) {
        console.warn('Health check failed:', error);
        showError('サーバーへの接続に失敗しました。サーバーが起動しているか確認してください。');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}
