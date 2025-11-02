# Frontend Tests

This directory contains unit tests for the frontend JavaScript modules.

## Running Tests

### Prerequisites

```bash
# Install Node.js and npm (if not already installed)
# Recommended: Node.js 18+ or 20+

# Install dependencies
cd frontend
npm install
```

### Test Commands

```bash
# Run all tests once
npm test

# Run tests in watch mode (auto-rerun on file changes)
npm run test:watch

# Run tests with coverage report
npm run test:coverage
```

### Coverage Reports

After running tests with coverage, you can view the detailed HTML report:

```bash
# Open coverage report in browser
open coverage/lcov-report/index.html  # macOS
xdg-open coverage/lcov-report/index.html  # Linux
```

## Test Files

- `api.test.js` - Tests for APIClient (HTTP request handling)
- `chart.test.js` - Tests for ChartManager (Chart.js wrapper)
- `trend.test.js` - Tests for TrendManager (period selection, data loading)
- `setup.js` - Jest configuration and global test setup

## Coverage Thresholds

The project enforces minimum coverage thresholds:

- **Branches**: 70%
- **Functions**: 70%
- **Lines**: 70%
- **Statements**: 70%

Tests will fail if coverage falls below these thresholds.

## Mocking

### Chart.js

Chart.js is mocked in `__mocks__/chart.js` to avoid depending on the actual Chart.js library in tests. The mock provides basic Chart class functionality for testing.

### Fetch API

The global `fetch` function is mocked in `tests/setup.js` for all tests. Each test can configure mock responses using Jest's mocking capabilities.

## Writing Tests

### Example: Testing API Client

```javascript
import { describe, test, expect, beforeEach, jest } from '@jest/globals';

describe('APIClient', () => {
    beforeEach(() => {
        global.fetch = jest.fn();
    });

    test('should fetch data successfully', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ data: 'test' }),
        });

        // Your test code here
    });
});
```

### Example: Testing Chart Manager

```javascript
describe('ChartManager', () => {
    beforeEach(() => {
        document.body.innerHTML = '<canvas id="test-chart"></canvas>';
    });

    test('should create chart', () => {
        const chartManager = new ChartManager('test-chart');
        chartManager.createPieChart(mockData);

        expect(chartManager.chart).not.toBeNull();
    });
});
```

## Continuous Integration

Tests are automatically run in CI/CD pipeline on every push and pull request. See `.github/workflows/frontend-ci.yml` for CI configuration.

## Troubleshooting

### Tests fail with "Cannot find module"

Make sure all dependencies are installed:

```bash
npm install
```

### Tests fail with "ReferenceError: Chart is not defined"

The Chart.js mock should be automatically loaded. Check that `__mocks__/chart.js` exists and `jest.config` in `package.json` includes the correct `moduleNameMapper`.

### Coverage reports are not generated

Run tests with the coverage flag:

```bash
npm run test:coverage
```

## Best Practices

1. **Test behavior, not implementation** - Focus on what the code does, not how it does it
2. **Use descriptive test names** - Test names should clearly describe what is being tested
3. **Keep tests isolated** - Each test should be independent and not rely on other tests
4. **Mock external dependencies** - Use mocks for API calls, DOM elements, and third-party libraries
5. **Test edge cases** - Include tests for error conditions, empty data, null values, etc.
6. **Maintain high coverage** - Aim for 80%+ coverage on critical modules

## Resources

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Testing Library](https://testing-library.com/docs/)
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
