/**
 * Jest test setup
 * Global configuration for all tests
 */

/* global global */

import '@testing-library/jest-dom';
import { jest, beforeEach } from '@jest/globals';

// Mock fetch globally
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
    jest.clearAllMocks();
    fetch.mockClear();
});

// Mock HTMLCanvasElement.prototype.getContext
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
    clearRect: jest.fn(),
    fillRect: jest.fn(),
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    beginPath: jest.fn(),
    arc: jest.fn(),
    fill: jest.fn(),
    stroke: jest.fn(),
    lineTo: jest.fn(),
    moveTo: jest.fn(),
    scale: jest.fn(),
    translate: jest.fn(),
    rotate: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    measureText: jest.fn(() => ({ width: 0 })),
    fillText: jest.fn(),
    strokeText: jest.fn(),
}));

// Setup DOM helpers
global.createMockCanvas = () => {
    const canvas = document.createElement('canvas');
    canvas.id = 'test-canvas';
    return canvas;
};

// Mock window.Chart
global.Chart = class Chart {
    constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config;
        this.type = config.type;
        this.data = config.data;
        this.options = config.options;
        this.destroyed = false;
    }
    destroy() {
        this.destroyed = true;
    }
    update() {}
    reset() {}
};
