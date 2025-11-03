/**
 * Assets Management - JavaScript Logic
 * TASK-1110: フロントエンド JavaScript 実装
 */

// API Configuration
const API_CONFIG = {
    host: localStorage.getItem('api_host') || 'localhost',
    port: localStorage.getItem('api_port') || '8000',
};

// State Management
const assetState = {
    assetClasses: [],
    records: [],
    summary: null,
    allocation: null,
    editingRecordId: null,
    deleteRecordId: null,
};

// Chart instances
let allocationPieChart = null;
let assetsBarChart = null;
let allocationDoughnutChart = null;

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    try {
        await loadAssetClasses();
        populateSelects();
        setupEventListeners();
        setupTabNavigation();

        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('record-date').value = today;
        document.getElementById('export-start-date').value = getFirstDayOfMonth();
        document.getElementById('export-end-date').value = today;
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('アプリケーションの初期化に失敗しました', 'overview-error');
    }
}

/**
 * Load asset classes from API
 */
async function loadAssetClasses() {
    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/classes`
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && Array.isArray(data.data)) {
            assetState.assetClasses = data.data;
        } else {
            throw new Error('Invalid API response format');
        }
    } catch (error) {
        console.error('Failed to load asset classes:', error);
        throw error;
    }
}

/**
 * Populate select dropdowns with years and months
 */
function populateSelects() {
    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();
    const currentMonth = currentDate.getMonth() + 1;

    // Generate years (2022-2025)
    const years = [];
    for (let year = 2022; year <= currentYear; year++) {
        years.push(year);
    }

    // Populate year selects
    const yearSelects = ['overview-year', 'allocation-year'];
    yearSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            select.innerHTML = years
                .map(year => `<option value="${year}" ${year === currentYear ? 'selected' : ''}>${year}</option>`)
                .join('');
        }
    });

    // Populate month selects
    const monthSelects = ['overview-month', 'allocation-month'];
    monthSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            select.innerHTML = Array.from({ length: 12 }, (_, i) => {
                const month = i + 1;
                return `<option value="${month}" ${month === currentMonth ? 'selected' : ''}>${month}月</option>`;
            }).join('');
        }
    });

    // Populate asset class selects
    const classSelects = ['asset-class', 'edit-asset-class', 'export-asset-class'];
    classSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            select.innerHTML = assetState.assetClasses
                .map(ac => `<option value="${ac.id}">${ac.display_name}</option>`)
                .join('');
        }
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Overview tab
    document.getElementById('load-overview-btn')?.addEventListener('click', loadOverviewData);

    // Records tab
    document.getElementById('add-record-form')?.addEventListener('submit', handleAddRecord);
    document.getElementById('refresh-records-btn')?.addEventListener('click', loadRecords);
    document.getElementById('record-search')?.addEventListener('input', filterRecords);

    // Allocation tab
    document.getElementById('load-allocation-btn')?.addEventListener('click', loadAllocationData);

    // Export tab
    document.getElementById('export-btn')?.addEventListener('click', handleExport);

    // Edit form
    document.getElementById('edit-record-form')?.addEventListener('submit', handleUpdateRecord);

    // Delete confirm
    document.getElementById('confirm-delete-btn')?.addEventListener('click', handleDeleteRecord);
}

/**
 * Setup tab navigation
 */
function setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Remove active class from all buttons and contents
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            document.getElementById(`${tabName}-tab`)?.classList.add('active');

            // Load data when switching to records tab
            if (tabName === 'records') {
                loadRecords();
            }
        });
    });
}

/**
 * Load overview data (summary + charts)
 */
async function loadOverviewData() {
    showLoading('overview-loading');
    clearError('overview-error');

    try {
        const year = document.getElementById('overview-year').value;
        const month = document.getElementById('overview-month').value;

        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/summary?year=${year}&month=${month}`
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.data) {
            assetState.summary = data.data;
            updateOverviewDisplay();
            await loadAllocationChart();
        } else {
            throw new Error('Invalid API response');
        }
    } catch (error) {
        console.error('Failed to load overview data:', error);
        showError(`データ読み込みエラー: ${error.message}`, 'overview-error');
    } finally {
        hideLoading('overview-loading');
    }
}

/**
 * Update overview display with summary data
 */
function updateOverviewDisplay() {
    if (!assetState.summary) return;

    const summary = assetState.summary;

    // Update summary cards
    document.getElementById('total-assets').textContent = formatCurrency(summary.total_balance);
    document.getElementById('month-change').textContent =
        `${summary.month_change_rate >= 0 ? '+' : ''}${summary.month_change_rate.toFixed(1)}%`;
    document.getElementById('max-assets').textContent = formatCurrency(summary.max_balance);
    document.getElementById('asset-class-count').textContent = `${summary.class_count}`;
}

/**
 * Load records for records tab
 */
async function loadRecords() {
    showLoading('records-loading');

    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/records`
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && Array.isArray(data.data)) {
            assetState.records = data.data;
            displayRecordsTable();
        } else {
            throw new Error('Invalid API response');
        }
    } catch (error) {
        console.error('Failed to load records:', error);
        showError(`レコード読み込みエラー: ${error.message}`);
    } finally {
        hideLoading('records-loading');
    }
}

/**
 * Display records in table
 */
function displayRecordsTable() {
    const tbody = document.getElementById('records-tbody');

    if (!tbody || assetState.records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">レコードがありません</td></tr>';
        return;
    }

    tbody.innerHTML = assetState.records
        .map(record => {
            const assetClass = assetState.assetClasses.find(ac => ac.id === record.asset_class_id);
            return `
                <tr>
                    <td>${new Date(record.record_date).toLocaleDateString('ja-JP')}</td>
                    <td>${assetClass?.display_name || ''}</td>
                    <td>${record.sub_asset_name}</td>
                    <td>${formatCurrency(record.amount)}</td>
                    <td>${record.memo || '-'}</td>
                    <td>
                        <div class="table-actions">
                            <button class="edit-btn" onclick="openEditModal(${record.id})">編集</button>
                            <button class="delete-btn" onclick="openDeleteConfirmModal(${record.id})">削除</button>
                        </div>
                    </td>
                </tr>
            `;
        })
        .join('');
}

/**
 * Filter records by search text
 */
function filterRecords() {
    const searchText = document.getElementById('record-search').value.toLowerCase();
    const tbody = document.getElementById('records-tbody');
    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchText) ? '' : 'none';
    });
}

/**
 * Handle add record form submission
 */
async function handleAddRecord(e) {
    e.preventDefault();

    const formData = {
        record_date: document.getElementById('record-date').value + 'T00:00:00',
        asset_class_id: parseInt(document.getElementById('asset-class').value),
        sub_asset_name: document.getElementById('asset-name').value,
        amount: parseFloat(document.getElementById('asset-amount').value),
        memo: document.getElementById('asset-memo').value || null,
    };

    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/records`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showMessage('レコードを追加しました ✓', 'form-message', 'success');
            document.getElementById('add-record-form').reset();
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('record-date').value = today;
            await loadRecords();
        } else {
            throw new Error(data.detail || 'Failed to add record');
        }
    } catch (error) {
        console.error('Failed to add record:', error);
        showMessage(`エラー: ${error.message}`, 'form-message', 'error');
    }
}

/**
 * Open edit modal for record
 */
async function openEditModal(recordId) {
    const record = assetState.records.find(r => r.id === recordId);
    if (!record) return;

    const assetClass = assetState.assetClasses.find(ac => ac.id === record.asset_class_id);

    document.getElementById('edit-record-id').value = record.id;
    document.getElementById('edit-record-date').value = record.record_date.split('T')[0];
    document.getElementById('edit-asset-class').value = record.asset_class_id;
    document.getElementById('edit-asset-name').value = record.sub_asset_name;
    document.getElementById('edit-asset-amount').value = record.amount;
    document.getElementById('edit-asset-memo').value = record.memo || '';

    document.getElementById('edit-modal').classList.remove('hidden');
    assetState.editingRecordId = recordId;
}

/**
 * Close edit modal
 */
function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
    document.getElementById('edit-message').classList.add('hidden');
    assetState.editingRecordId = null;
}

/**
 * Handle update record form submission
 */
async function handleUpdateRecord(e) {
    e.preventDefault();

    const recordId = parseInt(document.getElementById('edit-record-id').value);

    const formData = {
        record_date: document.getElementById('edit-record-date').value + 'T00:00:00',
        asset_class_id: parseInt(document.getElementById('edit-asset-class').value),
        sub_asset_name: document.getElementById('edit-asset-name').value,
        amount: parseFloat(document.getElementById('edit-asset-amount').value),
        memo: document.getElementById('edit-asset-memo').value || null,
    };

    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/records/${recordId}`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showMessage('レコードを更新しました ✓', 'edit-message', 'success');
            await new Promise(r => setTimeout(r, 1000));
            closeEditModal();
            await loadRecords();
        } else {
            throw new Error(data.detail || 'Failed to update record');
        }
    } catch (error) {
        console.error('Failed to update record:', error);
        showMessage(`エラー: ${error.message}`, 'edit-message', 'error');
    }
}

/**
 * Open delete confirm modal
 */
function openDeleteConfirmModal(recordId) {
    assetState.deleteRecordId = recordId;
    document.getElementById('delete-confirm-modal').classList.remove('hidden');
}

/**
 * Close delete confirm modal
 */
function closeDeleteConfirmModal() {
    document.getElementById('delete-confirm-modal').classList.add('hidden');
    assetState.deleteRecordId = null;
}

/**
 * Handle delete record
 */
async function handleDeleteRecord() {
    const recordId = assetState.deleteRecordId;
    if (!recordId) return;

    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/records/${recordId}`,
            { method: 'DELETE' }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            closeDeleteConfirmModal();
            await loadRecords();
        } else {
            throw new Error(data.detail || 'Failed to delete record');
        }
    } catch (error) {
        console.error('Failed to delete record:', error);
        alert(`削除エラー: ${error.message}`);
    }
}

/**
 * Load allocation data
 */
async function loadAllocationData() {
    showLoading('allocation-loading');
    clearError('allocation-error');

    try {
        const year = document.getElementById('allocation-year').value;
        const month = document.getElementById('allocation-month').value;

        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/allocation?year=${year}&month=${month}`
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.data) {
            assetState.allocation = data.data;
            displayAllocationTable();
            updateAllocationChart();
        } else {
            throw new Error('Invalid API response');
        }
    } catch (error) {
        console.error('Failed to load allocation data:', error);
        showError(`データ読み込みエラー: ${error.message}`, 'allocation-error');
    } finally {
        hideLoading('allocation-loading');
    }
}

/**
 * Display allocation table
 */
function displayAllocationTable() {
    const tbody = document.getElementById('allocation-tbody');

    if (!tbody || !assetState.allocation || assetState.allocation.length === 0) {
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">データがありません</td></tr>';
        }
        return;
    }

    const total = assetState.allocation.reduce((sum, item) => sum + item.balance, 0);

    tbody.innerHTML = assetState.allocation
        .map(item => {
            const percentage = total > 0 ? ((item.balance / total) * 100).toFixed(1) : 0;
            const barWidth = Math.min(percentage, 100);
            return `
                <tr>
                    <td>${item.class_display_name}</td>
                    <td>${formatCurrency(item.balance)}</td>
                    <td>${percentage}%</td>
                    <td>
                        <div class="progress-bar" style="width: 100%; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                            <div style="width: ${barWidth}%; background: #3b82f6; height: 20px; transition: width 0.3s ease;"></div>
                        </div>
                    </td>
                </tr>
            `;
        })
        .join('');
}

/**
 * Load allocation chart
 */
async function loadAllocationChart() {
    const year = document.getElementById('overview-year').value;
    const month = document.getElementById('overview-month').value;

    try {
        const response = await fetch(
            `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/allocation?year=${year}&month=${month}`
        );

        if (!response.ok) return;

        const data = await response.json();
        if (data.success && data.data) {
            updateAllocationPieChart(data.data);
            updateAssetsBarChart(data.data);
        }
    } catch (error) {
        console.error('Failed to load allocation chart data:', error);
    }
}

/**
 * Update allocation pie chart
 */
function updateAllocationPieChart(allocationData) {
    const ctx = document.getElementById('allocation-pie-chart');
    if (!ctx) return;

    const labels = allocationData.map(item => item.class_display_name);
    const values = allocationData.map(item => item.balance);

    if (allocationPieChart) {
        allocationPieChart.destroy();
    }

    allocationPieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'
                ],
                borderColor: '#ffffff',
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.label}: ${formatCurrency(context.parsed)}`,
                    },
                },
            },
        },
    });
}

/**
 * Update assets bar chart
 */
function updateAssetsBarChart(allocationData) {
    const ctx = document.getElementById('assets-bar-chart');
    if (!ctx) return;

    const labels = allocationData.map(item => item.class_display_name);
    const values = allocationData.map(item => item.balance);

    if (assetsBarChart) {
        assetsBarChart.destroy();
    }

    assetsBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '残高 (円)',
                data: values,
                backgroundColor: '#3b82f6',
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `${formatCurrency(context.parsed.y)}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => formatCurrency(value),
                    },
                },
            },
        },
    });
}

/**
 * Update allocation doughnut chart
 */
function updateAllocationChart() {
    const ctx = document.getElementById('allocation-doughnut-chart');
    if (!ctx || !assetState.allocation) return;

    const labels = assetState.allocation.map(item => item.class_display_name);
    const values = assetState.allocation.map(item => item.balance);

    if (allocationDoughnutChart) {
        allocationDoughnutChart.destroy();
    }

    allocationDoughnutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'
                ],
                borderColor: '#ffffff',
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.label}: ${formatCurrency(context.parsed)}`,
                    },
                },
            },
        },
    });
}

/**
 * Handle export
 */
async function handleExport() {
    const format = document.getElementById('export-format').value;
    const assetClassId = document.getElementById('export-asset-class').value || null;
    const startDate = document.getElementById('export-start-date').value;
    const endDate = document.getElementById('export-end-date').value;

    if (!startDate || !endDate) {
        showMessage('開始日と終了日を指定してください', 'export-message', 'error');
        return;
    }

    try {
        let url = `http://${API_CONFIG.host}:${API_CONFIG.port}/api/assets/export?format=${format}`;
        if (assetClassId) {
            url += `&asset_class_id=${assetClassId}`;
        }
        url += `&start_date=${startDate}&end_date=${endDate}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `assets_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);

        showMessage('ファイルをダウンロードしました ✓', 'export-message', 'success');
    } catch (error) {
        console.error('Failed to export:', error);
        showMessage(`エクスポートエラー: ${error.message}`, 'export-message', 'error');
    }
}

/**
 * Utility Functions
 */

function formatCurrency(value) {
    if (typeof value !== 'number' || isNaN(value)) return '¥0';
    return `¥${Math.round(value).toLocaleString('ja-JP')}`;
}

function getFirstDayOfMonth() {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1)
        .toISOString().split('T')[0];
}

function showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.remove('hidden');
}

function hideLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.add('hidden');
}

function showError(message, elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.remove('hidden');
    }
}

function clearError(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = '';
        el.classList.add('hidden');
    }
}

function showMessage(message, elementId, type = 'info') {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.className = `message ${type}`;
        el.classList.remove('hidden');

        if (type === 'success') {
            setTimeout(() => el.classList.add('hidden'), 3000);
        }
    }
}

/**
 * API Config Modal (shared functionality)
 */
function showApiConfigModal() {
    document.getElementById('api-config-modal').classList.remove('hidden');
    document.getElementById('api-host').value = API_CONFIG.host;
    document.getElementById('api-port').value = API_CONFIG.port;
}

function closeApiConfigModal() {
    document.getElementById('api-config-modal').classList.add('hidden');
}

document.getElementById('api-config-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    API_CONFIG.host = document.getElementById('api-host').value;
    API_CONFIG.port = document.getElementById('api-port').value;
    localStorage.setItem('api_host', API_CONFIG.host);
    localStorage.setItem('api_port', API_CONFIG.port);
    closeApiConfigModal();
    location.reload();
});
