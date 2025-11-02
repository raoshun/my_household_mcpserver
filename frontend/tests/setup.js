/**
 * Jest test setup
 * Global configuration for all tests
 */

import '@testing-library/jest-dom';

// Mock fetch globally
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
    jest.clearAllMocks();
    fetch.mockClear();
});

// Setup DOM helpers
global.createMockCanvas = () => {
    const canvas = document.createElement('canvas');
    canvas.id = 'test-canvas';
    canvas.getContext = jest.fn(() => ({
        clearRect: jest.fn(),
        fillRect: jest.fn(),
        beginPath: jest.fn(),
        arc: jest.fn(),
        fill: jest.fn(),
        stroke: jest.fn(),
    }));
    return canvas;
};

// Mock window.Chart
global.Chart = class Chart {
    constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config;
        this.destroyed = false;
    }
    destroy() {
        this.destroyed = true;
    }
    update() {}
    reset() {}
};
