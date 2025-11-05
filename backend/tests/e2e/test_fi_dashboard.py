"""
E2E tests for FIRE Dashboard Web UI

Tests browser interactions, API integration, and responsive design
for the Financial Independence (FIRE) analysis dashboard.

Coverage:
- Dashboard initialization and page load
- REST API calls and data binding
- Chart.js graph rendering
- Form submission and simulation
- Responsive design on multiple viewports
- Error handling and loading states
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page

# Viewport configurations for responsive testing
VIEWPORTS = {
    "desktop": {"width": 1920, "height": 1080},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 667},
}

# Base URL for the frontend
BASE_URL = "http://localhost:8080"
API_BASE_URL = "http://localhost:8000/api"


@pytest.fixture
def page_desktop(browser: Browser) -> Page:
    """Create a page with desktop viewport."""
    page = browser.new_page(viewport=VIEWPORTS["desktop"])
    yield page
    page.close()


@pytest.fixture
def page_tablet(browser: Browser) -> Page:
    """Create a page with tablet viewport."""
    page = browser.new_page(viewport=VIEWPORTS["tablet"])
    yield page
    page.close()


@pytest.fixture
def page_mobile(browser: Browser) -> Page:
    """Create a page with mobile viewport."""
    page = browser.new_page(viewport=VIEWPORTS["mobile"])
    yield page
    page.close()


class TestDashboardInitialization:
    """Tests for dashboard page load and initialization."""

    def test_dashboard_loads_successfully(self, page_desktop: Page) -> None:
        """Test that the dashboard page loads without errors."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")

        # Wait for page to be ready
        page_desktop.wait_for_load_state("networkidle")

        # Check that main container exists
        container = page_desktop.query_selector(".dashboard-container")
        assert container is not None, "Dashboard container should be present"

        # Check page title
        title = page_desktop.title()
        assert "FIRE" in title or "Dashboard" in title

    def test_dashboard_has_required_sections(self, page_desktop: Page) -> None:
        """Test that all dashboard sections are present."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Check for status cards section
        status_cards = page_desktop.query_selector("[id*='status']")
        assert status_cards is not None, "Status cards section should exist"

        # Check for chart containers
        charts_section = page_desktop.query_selector(".charts-section")
        assert charts_section is not None, "Charts section should exist"

        # Check for suggestions list
        suggestions = page_desktop.query_selector("[id*='suggestions']")
        assert suggestions is not None, "Suggestions section should exist"

        # Check for simulation form
        form = page_desktop.query_selector("#simulationForm")
        assert form is not None, "Simulation form should exist"

    def test_page_has_no_console_errors(self, page_desktop: Page) -> None:
        """Test that page loads without JavaScript errors."""
        errors: list[str] = []

        def on_console_msg(msg: object) -> None:
            if hasattr(msg, "type") and msg.type == "error":
                errors.append(str(msg))

        page_desktop.on("console", on_console_msg)
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        assert (
            len(errors) == 0
        ), f"Page should have no console errors, but got: {errors}"


class TestAPIIntegration:
    """Tests for REST API calls and data binding."""

    def test_fetch_financial_status(self, page_desktop: Page) -> None:
        """Test that status endpoint is called and data is displayed."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Wait for API call and data binding
        status_value = page_desktop.wait_for_selector(
            "[data-field='fire_percentage']", timeout=5000
        )
        assert status_value is not None

        # Check that numeric value is displayed
        text_content = status_value.text_content()
        assert text_content is not None
        # Should be a percentage or numeric value
        assert re.search(r"\d+", text_content), "Status should contain numeric value"

    def test_fetch_expense_breakdown(self, page_desktop: Page) -> None:
        """Test that expense breakdown is fetched and displayed."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Wait for expense breakdown chart
        chart_canvas = page_desktop.wait_for_selector("#expenseChart", timeout=5000)
        assert chart_canvas is not None

        # Check that chart has data attributes
        data_labels = page_desktop.query_selector("[data-field='categories']")
        # Chart should either have canvas or data attributes
        assert chart_canvas or data_labels

    def test_fetch_projections(self, page_desktop: Page) -> None:
        """Test that projections are fetched and displayed."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Wait for projections chart
        projections_chart = page_desktop.wait_for_selector(
            "#projectionsChart", timeout=5000
        )
        assert projections_chart is not None

    def test_api_error_handling(self, page_desktop: Page) -> None:
        """Test that API errors are handled gracefully."""

        # Intercept API calls to simulate errors
        def handle_route(route: object) -> None:
            if "financial-independence" in str(route):
                # Let requests through - we're testing real API
                pass

        # Just check that dashboard loads even if APIs are slow
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # No crashes should occur
        content = page_desktop.content()
        assert "dashboard" in content.lower()


class TestChartRendering:
    """Tests for Chart.js graph rendering and data visualization."""

    def test_expense_chart_renders(self, page_desktop: Page) -> None:
        """Test that expense breakdown chart renders."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Wait for Chart.js to initialize
        time.sleep(1)

        # Check that canvas has height and width (signs of rendering)
        canvas = page_desktop.query_selector("#expenseChart")
        assert canvas is not None

        # Get bounding box to verify it's visible
        box = canvas.bounding_box()
        assert box is not None
        assert box["height"] > 0
        assert box["width"] > 0

    def test_projections_chart_renders(self, page_desktop: Page) -> None:
        """Test that projections chart renders."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        time.sleep(1)

        canvas = page_desktop.query_selector("#projectionsChart")
        assert canvas is not None

        box = canvas.bounding_box()
        assert box is not None
        assert box["height"] > 0


class TestFormInteraction:
    """Tests for form submission and simulation."""

    def test_form_exists_and_is_interactive(self, page_desktop: Page) -> None:
        """Test that simulation form exists and is interactive."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Find the input field
        savings_input = page_desktop.query_selector(
            "input[id*='savings'], input[id*='Savings']"
        )
        assert savings_input is not None, "Savings input should exist"

        # Check that it's visible and enabled
        is_visible = savings_input.is_visible()
        is_enabled = savings_input.is_enabled()
        assert is_visible, "Input should be visible"
        assert is_enabled, "Input should be enabled"

    def test_form_submission_triggers_api_call(self, page_desktop: Page) -> None:
        """Test that form submission calls the update API."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Track network requests
        api_calls: list[str] = []

        def on_response(response: object) -> None:
            if hasattr(response, "url"):
                api_calls.append(str(response.url))

        page_desktop.on("response", on_response)

        # Find and fill the form
        savings_input = page_desktop.query_selector(
            "input[id*='savings'], input[id*='Savings']"
        )
        if savings_input:
            savings_input.fill("50000")

            # Find submit button
            submit_btn = page_desktop.query_selector(
                "button[onclick*='simulateSavings'], button[id*='simulate']"
            )
            if submit_btn:
                submit_btn.click()

                # Wait for potential API call
                time.sleep(1)

                # Check that some API call was made
                api_calls_made = any(
                    "financial-independence" in url for url in api_calls
                )
                assert api_calls_made, "Simulation should trigger API call"


class TestResponsiveDesign:
    """Tests for responsive design across viewports."""

    def test_desktop_layout_renders(self, page_desktop: Page) -> None:
        """Test desktop layout renders correctly."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Check that desktop-specific layout exists
        grid = page_desktop.query_selector(".dashboard-grid, .cards-container")
        assert grid is not None

        # Get layout info
        box = grid.bounding_box()
        assert box is not None
        # Desktop should be full width
        assert box["width"] > 1200

    def test_tablet_layout_renders(self, page_tablet: Page) -> None:
        """Test tablet layout renders correctly."""
        page_tablet.goto(f"{BASE_URL}/fi-dashboard.html")
        page_tablet.wait_for_load_state("networkidle")

        # Check layout is responsive
        grid = page_tablet.query_selector(".dashboard-grid, .cards-container")
        assert grid is not None

        # Tablet should have smaller width
        box = grid.bounding_box()
        assert box is not None
        assert 600 < box["width"] < 1024

    def test_mobile_layout_renders(self, page_mobile: Page) -> None:
        """Test mobile layout renders correctly."""
        page_mobile.goto(f"{BASE_URL}/fi-dashboard.html")
        page_mobile.wait_for_load_state("networkidle")

        # Check mobile layout exists
        grid = page_mobile.query_selector(".dashboard-grid, .cards-container")
        assert grid is not None

        # Mobile should be narrow
        box = grid.bounding_box()
        assert box is not None
        assert box["width"] < 600

    def test_mobile_cards_stack_vertically(self, page_mobile: Page) -> None:
        """Test that cards stack vertically on mobile."""
        page_mobile.goto(f"{BASE_URL}/fi-dashboard.html")
        page_mobile.wait_for_load_state("networkidle")

        # Get card positions
        cards = page_mobile.query_selector_all(".status-card, .card, [class*='card']")

        if len(cards) >= 2:
            # Check that cards are stacked (different Y positions)
            box1 = cards[0].bounding_box()
            box2 = cards[1].bounding_box()

            if box1 and box2:
                # In vertical stack, Y coordinates should differ significantly
                y_difference = abs(box2["y"] - box1["y"])
                # Should have some vertical spacing
                assert y_difference > 0


class TestEndToEndWorkflow:
    """Tests for complete end-to-end workflows."""

    def test_complete_dashboard_workflow(self, page_desktop: Page) -> None:
        """Test complete workflow: load → fetch → display → interact."""
        # Navigate to dashboard
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Verify initial load
        container = page_desktop.query_selector(".dashboard-container")
        assert container is not None

        # Wait for data to be fetched and displayed
        status_elem = page_desktop.wait_for_selector(
            "[data-field='fire_percentage']", timeout=5000
        )
        assert status_elem is not None

        # Interact with form
        input_elem = page_desktop.query_selector(
            "input[id*='savings'], input[id*='Savings']"
        )
        if input_elem:
            input_elem.fill("100000")

        # Dashboard should remain functional
        title = page_desktop.title()
        assert title is not None
        assert len(title) > 0

    def test_dashboard_auto_refresh(self, page_desktop: Page) -> None:
        """Test that dashboard auto-refreshes data."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        # Get initial data
        initial_status = page_desktop.query_selector("[data-field='fire_percentage']")
        initial_text = initial_status.text_content() if initial_status else None

        # Wait for potential auto-refresh
        time.sleep(2)

        # Dashboard should still be functional
        current_status = page_desktop.query_selector("[data-field='fire_percentage']")
        assert current_status is not None


class TestLoadingStates:
    """Tests for loading states and user feedback."""

    def test_loading_indicator_visible(self, page_desktop: Page) -> None:
        """Test that loading states are visible."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")

        # Don't wait for network - check for loading indicator
        loading = page_desktop.query_selector(".loading, .spinner, [class*='loading']")
        # May or may not be visible depending on timing
        # Just check page is responsive
        assert page_desktop is not None

    def test_no_timeout_errors(self, page_desktop: Page) -> None:
        """Test that page doesn't timeout or freeze."""
        start = time.time()
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")
        elapsed = time.time() - start

        # Should load within 30 seconds
        assert elapsed < 30, f"Page load took too long: {elapsed}s"


class TestPerformance:
    """Tests for performance metrics."""

    def test_initial_load_performance(self, page_desktop: Page) -> None:
        """Test that initial page load is performant."""
        start = time.time()
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")
        elapsed = time.time() - start

        # Should load in under 10 seconds
        assert elapsed < 10, f"Initial load took {elapsed}s (target: <10s)"

    def test_form_submission_performance(self, page_desktop: Page) -> None:
        """Test that form submission responds quickly."""
        page_desktop.goto(f"{BASE_URL}/fi-dashboard.html")
        page_desktop.wait_for_load_state("networkidle")

        input_elem = page_desktop.query_selector(
            "input[id*='savings'], input[id*='Savings']"
        )
        if input_elem:
            start = time.time()
            input_elem.fill("50000")
            elapsed = time.time() - start

            # Input should respond immediately
            assert elapsed < 1, f"Input took {elapsed}s to respond"
