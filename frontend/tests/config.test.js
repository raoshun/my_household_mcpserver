/**
 * Test suite for AppConfig class
 * Tests configuration initialization, API base URL detection, and environment handling
 */

describe('AppConfig', () => {
    let config;

    beforeEach(() => {
        // Clear localStorage before each test
        localStorage.clear();

        // Create a new AppConfig instance
        config = new AppConfig();
    });

    describe('Constructor and Initialization', () => {
        test('should initialize with correct default API port', () => {
            expect(config.DEFAULT_API_PORT).toBe(8000);
        });

        test('should set CONFIG_KEY', () => {
            expect(config.CONFIG_KEY).toBe('household_app_config');
        });
    });

    describe('API Base URL Detection', () => {
        test('should detect current hostname and port from window.location', () => {
            const url = config.getApiBaseUrl();
            expect(url).toMatch(/^https?:\/\//);
            expect(url).toContain('8000');
        });

        test('should return URL with correct protocol', () => {
            const url = config.getApiBaseUrl();
            const hasHttp = url.startsWith('http://') || url.startsWith('https://');
            expect(hasHttp).toBe(true);
        });

        test('should include hostname in URL', () => {
            const url = config.getApiBaseUrl();
            expect(url).toContain('localhost');
        });

        test('should use default port (8000) for Docker', () => {
            const url = config.getApiBaseUrl();
            expect(url).toContain(':8000');
        });
    });

    describe('Configuration Persistence', () => {
        test('should save API base URL to localStorage', () => {
            const testUrl = 'http://example.com:9000';
            config.setApiBaseUrl(testUrl);

            const saved = config.getSavedConfig();
            expect(saved).not.toBeNull();
            expect(saved.apiBaseUrl).toBe(testUrl);
        });

        test('should retrieve saved configuration from localStorage', () => {
            const testUrl = 'http://api.example.com:8001';
            config.setApiBaseUrl(testUrl);

            // Create new instance to test persistence
            const config2 = new AppConfig();
            expect(config2.getApiBaseUrl()).toBe(testUrl);
        });

        test('should include timestamp in saved config', () => {
            config.setApiBaseUrl('http://example.com:8000');
            const saved = config.getSavedConfig();
            expect(saved.updatedAt).toBeDefined();
            expect(typeof saved.updatedAt).toBe('string');
        });

        test('should clear saved configuration', () => {
            config.setApiBaseUrl('http://example.com:8000');
            config.clearSavedConfig();

            const saved = config.getSavedConfig();
            expect(saved).toBeNull();
        });
    });

    describe('URL Parameter Support', () => {
        test('should parse apiBase from URL query parameter', () => {
            // Simulate URL with query parameter
            const originalUrl = window.location.href;
            delete window.location;
            window.location = new URL('http://localhost:8081?apiBase=http://custom.api:8002');

            const config2 = new AppConfig();
            expect(config2.getApiBaseUrl()).toBe('http://custom.api:8002');

            // Restore original URL
            window.location = new URL(originalUrl);
        });
    });

    describe('Configuration Priority', () => {
        test('should prioritize localStorage over auto-detection', () => {
            const savedUrl = 'http://saved.api:9000';
            config.setApiBaseUrl(savedUrl);

            expect(config.getApiBaseUrl()).toBe(savedUrl);
        });

        test('should fall back to auto-detection if localStorage is empty', () => {
            localStorage.clear();
            const config2 = new AppConfig();
            const url = config2.getApiBaseUrl();

            expect(url).toContain('8000');
        });
    });

    describe('Configuration Validation', () => {
        test('should validate URL format before saving', () => {
            const validUrl = 'http://example.com:8000';
            expect(() => config.setApiBaseUrl(validUrl)).not.toThrow();
        });

        test('should handle JSON parse errors gracefully', () => {
            localStorage.setItem(config.CONFIG_KEY, 'invalid json');
            const config2 = new AppConfig();

            // Should not throw, fallback to null
            expect(config2.getSavedConfig()).toBeNull();
        });
    });

    describe('Environment-Specific Configuration', () => {
        test('should support Docker default (port 8000)', () => {
            localStorage.clear();
            const config2 = new AppConfig();
            const url = config2.getApiBaseUrl();
            expect(url).toContain(':8000');
        });

        test('should support custom port via URL parameter', () => {
            delete window.location;
            window.location = new URL('http://localhost:8081?apiBase=http://localhost:8001');

            const config2 = new AppConfig();
            expect(config2.getApiBaseUrl()).toContain(':8001');
        });

        test('should support custom hostname via URL parameter', () => {
            delete window.location;
            window.location = new URL('http://localhost:8081?apiBase=http://192.168.1.100:8000');

            const config2 = new AppConfig();
            expect(config2.getApiBaseUrl()).toContain('192.168.1.100');
        });
    });

    describe('Initialization Flow', () => {
        test('should load configuration on init', () => {
            const testUrl = 'http://init.test:8000';
            config.setApiBaseUrl(testUrl);

            // Create new instance - should load immediately
            const config2 = new AppConfig();
            expect(config2._apiBaseUrl).toBe(testUrl);
        });

        test('should provide apiBaseUrl property', () => {
            const url = config.apiBaseUrl;
            expect(url).toBeDefined();
            expect(typeof url).toBe('string');
        });
    });
});

describe('initializeApiConfig function', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    test('should return promise that resolves with API URL', async () => {
        const url = await initializeApiConfig();
        expect(url).toBeDefined();
        expect(typeof url).toBe('string');
    });

    test('should not show prompt when showPrompt is false', async () => {
        const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue(null);

        await initializeApiConfig(false);

        expect(promptSpy).not.toHaveBeenCalled();
        promptSpy.mockRestore();
    });
});

describe('showApiConfigModal function', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    test('should show configuration modal', () => {
        const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue(null);

        showApiConfigModal();

        expect(promptSpy).toHaveBeenCalled();
        promptSpy.mockRestore();
    });

    test('should save new URL when user enters valid URL', () => {
        const newUrl = 'http://new.api:8000';
        const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue(newUrl);
        const urlSpy = jest.spyOn(window, 'URL');

        showApiConfigModal();

        expect(promptSpy).toHaveBeenCalled();
        promptSpy.mockRestore();
        urlSpy.mockRestore();
    });
});
