// FIRE Dashboard JavaScript

const API_BASE_URL = 'http://localhost:8000/api';

let projectionChart = null;
let expenseChart = null;
let scenarioChart = null;

/**
 * Initialize dashboard and load data
 */
async function initDashboard() {
    console.log('Initializing FIRE dashboard...');
    await refreshDashboard();
}

/**
 * Refresh all dashboard data
 */
async function refreshDashboard() {
    try {
        console.log('Refreshing dashboard...');

        // Load status data
        const statusData = await fetchFinancialStatus();
        if (statusData) {
            updateStatusCards(statusData);
        }

        // Load expense patterns
        const expensesData = await fetchExpensePatterns();
        if (expensesData) {
            updateExpenseChart(expensesData);
        }

        // Load scenarios
        const scenariosData = await fetchScenarios();
        if (scenariosData) {
            updateScenarioChart(scenariosData);
        }

        // Load improvement suggestions
        const suggestionsData = await fetchSuggestions();
        if (suggestionsData) {
            updateSuggestions(suggestionsData);
        }

        // Update projection chart
        await updateProjectionData(statusData);

        updateLastUpdated();
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('ダッシュボードの読み込みに失敗しました');
    }
}

/**
 * Fetch financial independence status
 */
async function fetchFinancialStatus() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/financial-independence/status?period_months=12`
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching status:', error);
        return null;
    }
}

/**
 * Fetch expense patterns
 */
async function fetchExpensePatterns() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/financial-independence/expense-breakdown?period_months=12`
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching expense patterns:', error);
        return null;
    }
}

/**
 * Fetch financial scenarios
 */
async function fetchScenarios() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/financial-independence/projections?additional_monthly=0`
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching scenarios:', error);
        return null;
    }
}

/**
 * Fetch improvement suggestions
 */
async function fetchSuggestions() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/financial-independence/status?period_months=12`
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching suggestions:', error);
        return null;
    }
}

/**
 * Update status cards with data
 */
function updateStatusCards(data) {
    // Update progress
    const progressRate = data.progress_rate || 20;
    document.getElementById('progressFill').style.width = `${Math.min(progressRate, 100)}%`;
    document.getElementById('progressValue').textContent = progressRate.toFixed(1);

    // Update years to FI
    const yearsToFI = data.years_to_fi || 5.0;
    document.getElementById('yearsToFI').textContent = yearsToFI.toFixed(1);

    // Update current assets
    const currentAssets = data.current_assets || 5000000;
    document.getElementById('currentAssets').textContent =
        formatCurrency(currentAssets);

    // Update fire target
    const fireTarget = data.fire_target || 25000000;
    document.getElementById('fireTarget').textContent = formatCurrency(fireTarget);

    // Update monthly growth
    const monthlyGrowth = data.monthly_growth_rate || 0.01;
    document.getElementById('monthlyGrowth').textContent =
        `${(monthlyGrowth * 100).toFixed(2)}%`;

    // Update annual growth
    const annualGrowth = (Math.pow(1 + monthlyGrowth, 12) - 1) * 100;
    document.getElementById('annualGrowth').textContent =
        `${annualGrowth.toFixed(1)}%`;

    // Update annual expense
    const annualExpense = data.annual_expense || 1000000;
    document.getElementById('annualExpense').textContent =
        formatCurrency(annualExpense);

    // Fire expense is annual_expense
    document.getElementById('fireExpense').textContent =
        formatCurrency(annualExpense);
}

/**
 * Update projection chart
 */
async function updateProjectionData(statusData) {
    if (!statusData) return;

    const currentAssets = statusData.current_assets || 5000000;
    const fireTarget = statusData.fire_target || 25000000;
    const monthlyGrowth = statusData.monthly_growth_rate || 0.01;

    // Generate 60-month projection
    const labels = [];
    const projectionData = [];
    let currentValue = currentAssets;

    for (let i = 0; i <= 60; i += 6) {
        labels.push(`${i}ヶ月`);
        projectionData.push(Math.round(currentValue));
        for (let j = 0; j < 6 && i + j < 60; j++) {
            currentValue *= (1 + monthlyGrowth);
        }
    }

    // Destroy existing chart if it exists
    if (projectionChart) {
        projectionChart.destroy();
    }

    const ctx = document.getElementById('projectionChart');
    if (!ctx) return;

    projectionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '資産推移',
                    data: projectionData,
                    borderColor: '#2e7d32',
                    backgroundColor: 'rgba(46, 125, 50, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#2e7d32',
                    pointHoverRadius: 6,
                },
                {
                    label: 'FIRE目標',
                    data: Array(labels.length).fill(fireTarget),
                    borderColor: '#d32f2f',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                title: {
                    display: false,
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '¥' + formatNumber(value);
                        },
                    },
                },
            },
        },
    });
}

/**
 * Update expense breakdown chart
 */
function updateExpenseChart(data) {
    // Destroy existing chart if it exists
    if (expenseChart) {
        expenseChart.destroy();
    }

    const regularSpending = data.regular_spending || 600000;
    const irregularSpending = data.irregular_spending || 400000;

    const ctx = document.getElementById('expenseChart');
    if (!ctx) return;

    expenseChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['定期的支出', '不定期的支出'],
            datasets: [
                {
                    data: [regularSpending, irregularSpending],
                    backgroundColor: ['#2e7d32', '#ff9800'],
                    borderColor: ['#1b5e20', '#e65100'],
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '¥' + formatNumber(context.parsed);
                        },
                    },
                },
            },
        },
    });
}

/**
 * Update scenario comparison chart
 */
function updateScenarioChart(data) {
    // Destroy existing chart if it exists
    if (scenarioChart) {
        scenarioChart.destroy();
    }

    // Default scenarios
    const scenarios = [
        { name: '保守的', rate: 0.005, months: 240 },
        { name: '標準', rate: 0.01, months: 60 },
        { name: '積極的', rate: 0.02, months: 30 },
    ];

    const ctx = document.getElementById('scenarioChart');
    if (!ctx) return;

    scenarioChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: scenarios.map(s => s.name),
            datasets: [
                {
                    label: 'FIRE達成予定（年）',
                    data: scenarios.map(s => (s.months / 12).toFixed(1)),
                    backgroundColor: ['#1976d2', '#2e7d32', '#d32f2f'],
                    borderColor: ['#1565c0', '#1b5e20', '#b71c1c'],
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: true,
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                },
            },
        },
    });
}

/**
 * Update suggestions list
 */
function updateSuggestions(data) {
    const suggestionsList = document.getElementById('suggestionsList');
    if (!suggestionsList) return;

    // Default suggestions
    const suggestions = [
        {
            priority: 'HIGH',
            priority_ja: '🔴 高',
            title: '支出削減',
            description: '毎月の不定期支出を削減し、定期的支出のみに絞ることが重要です',
            impact: '月々50,000円削減で FIRE達成が1年短縮',
        },
        {
            priority: 'MEDIUM',
            priority_ja: '🟡 中',
            title: '収入増加',
            description: '副業やスキルアップにより月間収入を増加させることを検討してください',
            impact: '月々100,000円増加で FIRE達成が2年短縮',
        },
        {
            priority: 'LOW',
            priority_ja: '🟢 低',
            title: '資産運用の最適化',
            description: '現在の資産運用方法を見直し、リターンの向上を検討することも一つの選択肢です',
            impact: '年1%利回り向上で FIRE達成が1年短縮',
        },
    ];

    if (suggestions.length === 0) {
        suggestionsList.innerHTML = '<p class="loading">提案がありません</p>';
        return;
    }

    suggestionsList.innerHTML = suggestions
        .map(
            suggestion => `
        <div class="suggestion-item ${suggestion.priority.toLowerCase()}">
            <div class="suggestion-header">
                <span class="suggestion-priority">${suggestion.priority_ja}</span>
                <span class="suggestion-title">${suggestion.title}</span>
            </div>
            <p class="suggestion-description">${suggestion.description}</p>
            <p class="suggestion-impact">📈 ${suggestion.impact}</p>
        </div>
    `
        )
        .join('');
}

/**
 * Simulate additional savings impact
 */
async function simulateSavings() {
    const additionalInput = document.getElementById('additionalSavings');
    const additionalSavings = parseFloat(additionalInput.value) || 0;

    if (additionalSavings <= 0) {
        alert('0より大きい金額を入力してください');
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE_URL}/financial-independence/projections?` +
            `additional_monthly=${additionalSavings}`
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Show results
        const currentMonths = data.current_scenario?.months_to_fi || 60;
        const newMonths = data.with_additional_savings?.months_to_fi || 30;
        const monthsSaved = currentMonths - newMonths;
        const yearsSaved = (monthsSaved / 12).toFixed(1);
        const newYearsToFI = (newMonths / 12).toFixed(1);

        document.getElementById('yearsSaved').textContent = yearsSaved;
        document.getElementById('newFIDate').textContent = `${newYearsToFI}年後`;

        const resultDiv = document.getElementById('simulationResult');
        resultDiv.style.display = 'block';

        // Scroll to result
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Error simulating savings:', error);
        showError('シミュレーションに失敗しました');
    }
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
    document.getElementById('lastUpdated').textContent = `最終更新: ${timeStr}`;
}

/**
 * Format currency value
 */
function formatCurrency(value) {
    return '¥' + formatNumber(value);
}

/**
 * Format number with commas
 */
function formatNumber(value) {
    return Math.round(value).toLocaleString('ja-JP');
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #d32f2f;
        color: white;
        padding: 15px 20px;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        max-width: 400px;
    `;
    document.body.appendChild(errorDiv);

    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

/**
 * Initialize asset input form
 */
function initAssetInputForm() {
    // Populate year select
    const yearSelect = document.getElementById('assetYear');
    const monthSelect = document.getElementById('assetMonth');

    const now = new Date();
    const currentYear = now.getFullYear();

    // Add years (current year to 3 years back)
    for (let i = currentYear; i >= currentYear - 3; i--) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `${i}年`;
        yearSelect.appendChild(option);
    }

    // Add months
    for (let i = 1; i <= 12; i++) {
        const option = document.createElement('option');
        option.value = String(i).padStart(2, '0');
        option.textContent = `${i}月`;
        monthSelect.appendChild(option);
    }

    // Set current month as default
    yearSelect.value = currentYear;
    monthSelect.value = String(now.getMonth() + 1).padStart(2, '0');
}

/**
 * Save asset record to server
 */
async function saveAssetRecord() {
    const year = document.getElementById('assetYear').value;
    const month = document.getElementById('assetMonth').value;
    const assetType = document.getElementById('assetType').value;
    const amount = parseFloat(document.getElementById('assetAmount').value);

    if (!amount || amount <= 0) {
        showError('金額を正しく入力してください');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/financial-independence/add-asset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                year: parseInt(year),
                month: parseInt(month),
                asset_type: assetType,
                amount: amount,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'エラーが発生しました');
        }

        const result = await response.json();

        // Show success message
        const resultDiv = document.getElementById('assetResult');
        const messageDiv = document.getElementById('assetMessage');
        messageDiv.textContent = `✅ 資産を記録しました（${result.asset_type}）`;
        resultDiv.style.display = 'block';

        // Clear form
        document.getElementById('assetAmount').value = '';

        // Refresh dashboard after 1 second
        setTimeout(() => {
            refreshDashboard();
        }, 1000);

    } catch (error) {
        console.error('Error saving asset:', error);
        showError(`資産の記録に失敗しました: ${error.message}`);
    }
}

/**
 * Delete asset record from server
 */
async function deleteAssetRecord() {
    const year = document.getElementById('assetYear').value;
    const month = document.getElementById('assetMonth').value;
    const assetType = document.getElementById('assetType').value;

    if (!confirm(`${year}年${month}月の${assetType}を削除してもよろしいですか？`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/financial-independence/delete-asset`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                year: parseInt(year),
                month: parseInt(month),
                asset_type: assetType,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'エラーが発生しました');
        }

        // Show success message
        const resultDiv = document.getElementById('assetResult');
        const messageDiv = document.getElementById('assetMessage');
        messageDiv.textContent = `✅ 資産を削除しました`;
        resultDiv.style.display = 'block';

        // Refresh dashboard after 1 second
        setTimeout(() => {
            refreshDashboard();
        }, 1000);

    } catch (error) {
        console.error('Error deleting asset:', error);
        showError(`資産の削除に失敗しました: ${error.message}`);
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    initAssetInputForm();
    initDashboard();
});

// Refresh every 5 minutes
setInterval(refreshDashboard, 5 * 60 * 1000);
