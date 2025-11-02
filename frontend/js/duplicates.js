/**
 * Duplicate Detection Module
 * Handles duplicate transaction detection and resolution UI
 */

class DuplicateManager {
    constructor() {
        this.apiClient = new APIClient();
        this.init();
    }

    init() {
        // Bind event listeners
        document
            .getElementById('detect-btn')
            .addEventListener('click', () => this.detectDuplicates());
        document
            .getElementById('load-candidates-btn')
            .addEventListener('click', () => this.loadCandidates());
        document
            .getElementById('refresh-stats-btn')
            .addEventListener('click', () => this.loadStats());

        // Load initial stats
        this.loadStats();
    }

    /**
     * Detect duplicate transactions
     */
    async detectDuplicates() {
        const dateTolerance = parseInt(document.getElementById('date-tolerance').value) || 0;
        const amountToleranceAbs =
            parseFloat(document.getElementById('amount-tolerance-abs').value) || 0;
        const amountTolerancePct =
            parseFloat(document.getElementById('amount-tolerance-pct').value) || 0;

        const resultDiv = document.getElementById('detection-result');
        resultDiv.textContent = '検出中...';
        resultDiv.className = 'result-message';

        try {
            const response = await fetch(
                `${this.apiClient.baseUrl}/api/duplicates/detect?` +
                    `date_tolerance_days=${dateTolerance}&` +
                    `amount_tolerance_abs=${amountToleranceAbs}&` +
                    `amount_tolerance_pct=${amountTolerancePct}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                resultDiv.textContent =
                    data.message || `${data.detected_count}件の重複候補を検出しました`;
                resultDiv.className = 'result-message success';

                // Reload stats and candidates
                await this.loadStats();
                await this.loadCandidates();
            } else {
                resultDiv.textContent = `エラー: ${data.error}`;
                resultDiv.className = 'result-message error';
            }
        } catch (error) {
            console.error('Error detecting duplicates:', error);
            resultDiv.textContent = `エラー: ${error.message}`;
            resultDiv.className = 'result-message error';
        }
    }

    /**
     * Load duplicate candidates
     */
    async loadCandidates(limit = 10) {
        const container = document.getElementById('candidates-container');
        container.innerHTML = '<div class="loading">候補を読み込み中</div>';

        try {
            const response = await fetch(
                `${this.apiClient.baseUrl}/api/duplicates/candidates?limit=${limit}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.candidates && data.candidates.length > 0) {
                container.innerHTML = '';
                data.candidates.forEach((candidate) => {
                    container.appendChild(this.createCandidateCard(candidate));
                });
            } else if (data.success && data.candidates.length === 0) {
                container.innerHTML = '<p class="placeholder">未判定の重複候補はありません</p>';
            } else {
                container.innerHTML = `<p class="placeholder error">エラー: ${data.error}</p>`;
            }
        } catch (error) {
            console.error('Error loading candidates:', error);
            container.innerHTML = `<p class="placeholder error">エラー: ${error.message}</p>`;
        }
    }

    /**
     * Load duplicate statistics
     */
    async loadStats() {
        try {
            const response = await fetch(`${this.apiClient.baseUrl}/api/duplicates/stats`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.stats) {
                document.getElementById('pending-count').textContent = data.stats.pending || 0;
                document.getElementById('duplicate-count').textContent = data.stats.duplicate || 0;
                document.getElementById('not-duplicate-count').textContent =
                    data.stats.not_duplicate || 0;
                document.getElementById('skipped-count').textContent = data.stats.skipped || 0;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    /**
     * Create a candidate card element
     */
    createCandidateCard(candidate) {
        const card = document.createElement('div');
        card.className = 'candidate-card';
        card.dataset.checkId = candidate.check_id;

        // Header
        const header = document.createElement('div');
        header.className = 'candidate-header';
        header.innerHTML = `
            <span class="candidate-id">候補 #${candidate.check_id}</span>
            <span class="similarity-score">類似度: ${(candidate.similarity_score * 100).toFixed(0)}%</span>
        `;
        card.appendChild(header);

        // Comparison grid
        const grid = document.createElement('div');
        grid.className = 'comparison-grid';

        // Transaction 1
        const col1 = this.createTransactionColumn('取引 1', candidate.transaction_1);
        grid.appendChild(col1);

        // Transaction 2
        const col2 = this.createTransactionColumn('取引 2', candidate.transaction_2);
        grid.appendChild(col2);

        card.appendChild(grid);

        // Action buttons
        const actions = document.createElement('div');
        actions.className = 'action-buttons';
        actions.innerHTML = `
            <button class="btn-primary btn-duplicate" data-decision="duplicate">重複である</button>
            <button class="btn-primary btn-not-duplicate" data-decision="not_duplicate">重複でない</button>
            <button class="btn-primary btn-skip" data-decision="skip">スキップ</button>
        `;
        card.appendChild(actions);

        // Add event listeners to action buttons
        actions.querySelectorAll('button').forEach((btn) => {
            btn.addEventListener('click', () => {
                const decision = btn.dataset.decision;
                this.confirmDuplicate(candidate.check_id, decision, card);
            });
        });

        return card;
    }

    /**
     * Create a transaction column
     */
    createTransactionColumn(title, transaction) {
        const col = document.createElement('div');
        col.className = 'transaction-column';

        const html = `
            <h4>${title}</h4>
            <div class="transaction-field">
                <span class="field-label">ID:</span>
                <span class="field-value">${transaction.id}</span>
            </div>
            <div class="transaction-field">
                <span class="field-label">日付:</span>
                <span class="field-value">${transaction.date}</span>
            </div>
            <div class="transaction-field">
                <span class="field-label">金額:</span>
                <span class="field-value amount">¥${this.formatCurrency(transaction.amount)}</span>
            </div>
            <div class="transaction-field">
                <span class="field-label">摘要:</span>
                <span class="field-value">${this.escapeHtml(transaction.description || '-')}</span>
            </div>
            <div class="transaction-field">
                <span class="field-label">カテゴリ:</span>
                <span class="field-value">${this.escapeHtml(transaction.category || '-')}</span>
            </div>
            ${
                transaction.subcategory
                    ? `
            <div class="transaction-field">
                <span class="field-label">サブカテゴリ:</span>
                <span class="field-value">${this.escapeHtml(transaction.subcategory)}</span>
            </div>
            `
                    : ''
            }
        `;

        col.innerHTML = html;
        return col;
    }

    /**
     * Confirm duplicate decision
     */
    async confirmDuplicate(checkId, decision, cardElement) {
        try {
            const response = await fetch(
                `${this.apiClient.baseUrl}/api/duplicates/${checkId}/confirm?decision=${decision}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                // Remove card with animation
                cardElement.style.opacity = '0';
                cardElement.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    cardElement.remove();

                    // Check if there are any candidates left
                    const container = document.getElementById('candidates-container');
                    if (container.children.length === 0) {
                        container.innerHTML =
                            '<p class="placeholder">すべての候補を判定しました</p>';
                    }
                }, 300);

                // Reload stats
                await this.loadStats();
            } else {
                alert(`エラー: ${data.error}`);
            }
        } catch (error) {
            console.error('Error confirming duplicate:', error);
            alert(`エラー: ${error.message}`);
        }
    }

    /**
     * Format currency
     */
    formatCurrency(value) {
        return Math.abs(value).toLocaleString('ja-JP');
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new DuplicateManager();
});
