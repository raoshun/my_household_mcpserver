/**
 * MCP Tools Execution Frontend
 * ツール一覧の取得、実行、結果表示の管理
 */

/**
 * グローバル状態管理
 */
const mcpToolsState = {
    tools: [],
    currentTool: null,
    executionInProgress: false
};

/**
 * ページロード時の初期化
 */
document.addEventListener('DOMContentLoaded', () => {
    loadTools();
    setupKeyboardHandling();
    setupAccessibility();
});

/**
 * キーボードナビゲーション設定
 */
function setupKeyboardHandling() {
    document.addEventListener('keydown', (event) => {
        // Esc キーでモーダルを閉じる
        if (event.key === 'Escape') {
            const modal = document.getElementById('execute-modal');
            if (modal && !modal.classList.contains('hidden')) {
                closeToolModal();
                event.preventDefault();
            }
        }
    });

    // モーダルオーバーレイクリックで閉じる
    const modal = document.getElementById('execute-modal');
    const overlay = modal?.querySelector('.modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeToolModal);
    }
}

/**
 * アクセシビリティ設定
 */
function setupAccessibility() {
    // フォーカストラップ設定 (モーダル内のタブキー制御)
    const modal = document.getElementById('execute-modal');
    if (modal) {
        modal.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                const focusableElements = modal.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (event.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement.focus();
                        event.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement.focus();
                        event.preventDefault();
                    }
                }
            }
        });
    }
}

/**
 * Load tools list from API and render gallery
 */
async function loadTools() {
    try {
        mcpToolsState.executionInProgress = true;
        document.getElementById('tools-gallery').innerHTML =
            '<div class="loading">ツール一覧を読み込み中...</div>';

        const response = await fetch('/api/tools');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (!result.success || !result.data) {
            throw new Error('Invalid response format from API');
        }

        mcpToolsState.tools = result.data;
        renderToolsGallery(mcpToolsState.tools);
    } catch (error) {
        console.error('Error loading tools:', error);
        document.getElementById('tools-gallery').innerHTML =
            `<div class="error">ツール一覧の読み込みに失敗しました: ${error.message}</div>`;
    } finally {
        mcpToolsState.executionInProgress = false;
    }
}

/**
 * ツールギャラリーを動的生成
 */
function renderToolsGallery(tools) {
    const gallery = document.getElementById('tools-gallery');
    gallery.innerHTML = '';

    if (tools.length === 0) {
        gallery.innerHTML = '<p>利用可能なツールがありません</p>';
        return;
    }

    tools.forEach(tool => {
        const card = createToolCard(tool);
        gallery.appendChild(card);
    });
}

/**
 * ツールカード要素を作成
 */
function createToolCard(tool) {
    const card = document.createElement('div');
    card.className = 'tool-card';

    const requiredParamNames = (tool.parameters?.required || [])
        .map(p => p.name)
        .join(', ') || 'なし';

    const optionalParamNames = (tool.parameters?.optional || [])
        .map(p => p.name)
        .join(', ') || 'なし';

    const button = document.createElement('button');
    button.className = 'execute-button';
    button.setAttribute('aria-label', `${tool.display_name || tool.name} を実行`);
    button.innerHTML = '🚀 このツールを実行';
    button.addEventListener('click', () => openToolModal(tool.name));

    card.innerHTML = `
        <h3>${escapeHtml(tool.display_name || tool.name)}</h3>
        <p class="description">${escapeHtml(tool.description || '')}</p>
        <div class="category">
            <span class="badge">${escapeHtml(tool.category || '一般')}</span>
        </div>
        <div class="parameters" aria-label="パラメータ情報">
            <p><strong>必須パラメータ:</strong> ${escapeHtml(requiredParamNames)}</p>
            <p><strong>オプション:</strong> ${escapeHtml(optionalParamNames)}</p>
        </div>
    `;

    card.appendChild(button);
    return card;
}

/**
 * ツール実行モーダルを表示
 */
function openToolModal(toolName) {
    const tool = mcpToolsState.tools.find(t => t.name === toolName);
    if (!tool) {
        console.error(`Tool not found: ${toolName}`);
        return;
    }

    mcpToolsState.currentTool = tool;

    // モーダル内容を更新
    document.getElementById('modal-title').textContent = tool.display_name || tool.name;
    document.getElementById('modal-description').textContent = tool.description || '';

    // フォーム生成
    const form = document.getElementById('tool-form');
    form.innerHTML = createParameterForm(tool);

    // 実行結果をクリア
    const resultDiv = document.getElementById('execution-result');
    resultDiv.classList.add('hidden');
    resultDiv.innerHTML = '';

    // モーダルを表示
    const modal = document.getElementById('execute-modal');
    modal.classList.remove('hidden');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'modal-title');

    // フォーカスを最初の入力要素に移動
    setTimeout(() => {
        const firstInput = form.querySelector('input, select, textarea, button');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);
}

/**
 * モーダルを閉じる
 */
function closeToolModal() {
    const modal = document.getElementById('execute-modal');
    modal.classList.add('hidden');
    mcpToolsState.currentTool = null;
}

/**
 * パラメータフォームを生成
 */
function createParameterForm(tool) {
    let html = '';

    const required = tool.parameters?.required || [];
    const optional = tool.parameters?.optional || [];

    if (required.length > 0) {
        html += '<fieldset><legend>必須パラメータ</legend>';
        required.forEach(param => {
            html += createParameterInput(param, true);
        });
        html += '</fieldset>';
    }

    if (optional.length > 0) {
        html += '<fieldset><legend>オプションパラメータ</legend>';
        optional.forEach(param => {
            html += createParameterInput(param, false);
        });
        html += '</fieldset>';
    }

    if (required.length === 0 && optional.length === 0) {
        html += '<p>パラメータはありません</p>';
    }

    return html;
}

/**
 * パラメータ入力フィールドを生成
 */
function createParameterInput(param, isRequired) {
    const fieldId = `param_${param.name}`;
    const required = isRequired ? 'required' : '';
    const defaultValue = param.default !== null && param.default !== undefined ? param.default : '';
    const descId = `desc_${param.name}`;

    let input = '';

    if (param.choices && Array.isArray(param.choices)) {
        input = `
            <select id="${fieldId}" name="${param.name}" ${required} aria-describedby="${descId}">
                <option value="">-- 選択してください --</option>
                ${param.choices.map(choice => `
                    <option value="${escapeHtml(choice)}" ${choice === defaultValue ? 'selected' : ''}>
                        ${escapeHtml(choice)}
                    </option>
                `).join('')}
            </select>
        `;
    } else {
        let inputType = 'text';
        let inputAttrs = '';

        switch (param.type) {
            case 'integer':
                inputType = 'number';
                inputAttrs = 'step="1"';
                break;
            case 'number':
                inputType = 'number';
                inputAttrs = 'step="0.01"';
                break;
            case 'date':
                inputType = 'date';
                break;
        }

        input = `
            <input
                type="${inputType}"
                id="${fieldId}"
                name="${param.name}"
                placeholder="${escapeHtml(param.description || '')}"
                value="${escapeHtml(defaultValue.toString())}"
                ${inputAttrs}
                ${required}
                aria-describedby="${descId}"
            >
        `;
    }

    return `
        <div class="form-group">
            <label for="${fieldId}">${escapeHtml(param.name)}</label>
            <small id="${descId}">${escapeHtml(param.description || '')}</small>
            ${input}
        </div>
    `;
}

/**
 * ツールを実行
 */
async function executeTool() {
    const tool = mcpToolsState.currentTool;
    if (!tool || mcpToolsState.executionInProgress) {
        return;
    }

    mcpToolsState.executionInProgress = true;
    const executeButton = document.getElementById('execute-button');
    executeButton.disabled = true;

    const form = document.getElementById('tool-form');
    const formData = new FormData(form);
    const params = Object.fromEntries(formData.entries());

    // パラメータ型変換
    const convertedParams = convertParameters(tool, params);

    try {
        const response = await fetch(`/api/tools/${encodeURIComponent(tool.name)}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(convertedParams)
        });

        const data = await response.json();
        displayExecutionResult(data);
    } catch (error) {
        console.error('ツール実行失敗:', error);
        displayExecutionResult({
            success: false,
            error: '実行に失敗しました',
            error_code: 'EXECUTION_ERROR',
            details: error.message
        });
    } finally {
        mcpToolsState.executionInProgress = false;
        executeButton.disabled = false;
    }
}

/**
 * パラメータ型を変換
 */
function convertParameters(tool, params) {
    const converted = {};

    const allParams = [
        ...(tool.parameters?.required || []),
        ...(tool.parameters?.optional || [])
    ];

    for (const param of allParams) {
        if (!(param.name in params)) continue;

        let value = params[param.name];
        if (value === '') continue; // 空の値は除外

        switch (param.type) {
            case 'integer':
                converted[param.name] = parseInt(value, 10);
                break;
            case 'number':
                converted[param.name] = parseFloat(value);
                break;
            default:
                converted[param.name] = value;
        }
    }

    return converted;
}

/**
 * 実行結果を表示
 */
function displayExecutionResult(result) {
    const resultDiv = document.getElementById('execution-result');

    if (result.success) {
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div class="success-result">
                <h4>✅ 実行成功</h4>
                <p>実行時間: ${result.execution_time_ms}ms</p>
                <div class="result-data">
                    ${formatResultData(result.result)}
                </div>
            </div>
        `;
    } else {
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div class="error-result">
                <h4>❌ エラー</h4>
                <p>${escapeHtml(result.error || '不明なエラーが発生しました')}</p>
                ${result.error_code ? `<p class="error-code">エラーコード: ${escapeHtml(result.error_code)}</p>` : ''}
                ${result.details ? `<p class="error-code">詳細: ${escapeHtml(result.details)}</p>` : ''}
            </div>
        `;
    }
}

/**
 * 結果データを整形
 */
function formatResultData(result) {
    if (!result) {
        return '<p>データなし</p>';
    }

    let html = '';

    // サマリー表示
    if (result.summary && typeof result.summary === 'object') {
        html += '<div class="result-summary"><h5>サマリー</h5><ul>';
        for (const [key, value] of Object.entries(result.summary)) {
            html += `<li><strong>${escapeHtml(key)}:</strong> ${escapeHtml(formatValue(value))}</li>`;
        }
        html += '</ul></div>';
    }

    // テーブル表示
    if (result.data && Array.isArray(result.data) && result.data.length > 0) {
        const firstRow = result.data[0];
        const keys = Object.keys(firstRow);

        html += '<table class="result-table"><thead><tr>';
        keys.forEach(key => {
            html += `<th>${escapeHtml(key)}</th>`;
        });
        html += '</tr></thead><tbody>';

        result.data.forEach(row => {
            html += '<tr>';
            keys.forEach(key => {
                html += `<td>${escapeHtml(formatValue(row[key]))}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
    }

    if (html === '') {
        html = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
    }

    return html;
}

/**
 * 値をフォーマット
 */
function formatValue(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    if (typeof value === 'number') {
        if (Number.isInteger(value)) {
            return value.toLocaleString('ja-JP');
        } else {
            return value.toLocaleString('ja-JP', { maximumFractionDigits: 2 });
        }
    }
    if (typeof value === 'boolean') {
        return value ? 'はい' : 'いいえ';
    }
    return value.toString();
}

/**
 * エラーメッセージを表示
 */
function showError(message) {
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

/**
 * HTML エスケープ
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, char => map[char]);
}
