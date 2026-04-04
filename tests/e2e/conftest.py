"""E2E test fixtures – Playwright-based smoke tests."""

import os

import pytest

try:
    from playwright.sync_api import Page
except ImportError:
    Page = None


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
TEST_USER = os.getenv("E2E_TEST_USER", "taake")
TEST_PASSWORD = os.getenv("E2E_TEST_PASSWORD", "")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture()
def authenticated_page(page: Page, base_url):
    """Log in and return an authenticated page."""
    page.goto(f"{base_url}/app")
    page.wait_for_url("**/app#/login", timeout=5000)
    page.fill('input[type="text"]', TEST_USER)
    page.fill('input[type="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/app#/dashboard", timeout=10000)
    yield page
