/**
 * Mock for Chart.js
 * Used in Jest tests to avoid depending on the actual Chart.js library
 */

export class Chart {
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

    update() {
        // Mock update
    }

    reset() {
        // Mock reset
    }
}

export default Chart;

// Mock for global Chart object
global.Chart = Chart;
