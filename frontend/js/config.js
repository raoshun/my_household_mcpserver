/**
 * Application Configuration
 * Handles dynamic API base URL configuration
 */

class AppConfig {
    constructor() {
        this.CONFIG_KEY = 'household_app_config';
        this.DEFAULT_API_PORT = 8000;  // Docker: 8000, Local dev: 8001
        this.load();
    }

    /**
     * Get or initialize API base URL
     * Priority: localStorage > URL param > auto-detect > prompt
     */
    getApiBaseUrl() {
        // 1. Check localStorage for saved config
        const saved = this.getSavedConfig();
        if (saved?.apiBaseUrl) {
            return saved.apiBaseUrl;
        }

        // 2. Check URL query parameter
        const urlParams = new URLSearchParams(window.location.search);
        const urlApiBase = urlParams.get('apiBase');
        if (urlApiBase) {
            this.setApiBaseUrl(urlApiBase);
            return urlApiBase;
        }

        // 3. Auto-detect: same host, different port
        const autoUrl = `${window.location.protocol}//${window.location.hostname}:${this.DEFAULT_API_PORT}`;
        return autoUrl;
    }

    /**
     * Set and save API base URL
     */
    setApiBaseUrl(url) {
        const config = this.getSavedConfig() || {};
        config.apiBaseUrl = url;
        config.updatedAt = new Date().toISOString();
        localStorage.setItem(this.CONFIG_KEY, JSON.stringify(config));
    }

    /**
     * Get saved configuration
     */
    getSavedConfig() {
        try {
            const data = localStorage.getItem(this.CONFIG_KEY);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Failed to parse config:', e);
            return null;
        }
    }

    /**
     * Clear saved configuration
     */
    clearSavedConfig() {
        localStorage.removeItem(this.CONFIG_KEY);
    }

    /**
     * Load configuration (internal)
     */
    load() {
        this._apiBaseUrl = this.getApiBaseUrl();
    }

    /**
     * Get current API base URL
     */
    get apiBaseUrl() {
        return this._apiBaseUrl;
    }
}

// Global instance
const appConfig = new AppConfig();

/**
 * Initialize configuration with optional prompt
 * Call this in main page startup
 */
function initializeApiConfig(showPrompt = false) {
    return new Promise((resolve) => {
        const currentUrl = appConfig.getApiBaseUrl();

        if (showPrompt) {
            const userUrl = prompt(
                'API サーバーの URL を入力してください:\n' +
                `(現在の設定: ${currentUrl})`,
                currentUrl
            );

            if (userUrl && userUrl.trim()) {
                const validUrl = userUrl.trim();
                // Validate URL format
                try {
                    new URL(validUrl);
                    appConfig.setApiBaseUrl(validUrl);
                    resolve(validUrl);
                } catch (e) {
                    alert('無効な URL です。デフォルト設定を使用します。');
                    resolve(currentUrl);
                }
            } else {
                resolve(currentUrl);
            }
        } else {
            resolve(currentUrl);
        }
    });
}

/**
 * Show configuration UI (optional modal)
 */
function showApiConfigModal() {
    const currentUrl = appConfig.getApiBaseUrl();
    const newUrl = prompt(
        'API サーバーの URL を入力:\n' +
        '例: http://192.168.1.100:8001\n' +
        `現在: ${currentUrl}`,
        currentUrl
    );

    if (newUrl && newUrl.trim()) {
        try {
            new URL(newUrl);
            appConfig.setApiBaseUrl(newUrl.trim());
            location.reload();
        } catch (e) {
            alert('無効な URL です。');
        }
    }
}
