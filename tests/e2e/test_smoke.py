"""E2E Smoke Tests – kritische User-Flows der WebApp."""

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


class TestLogin:
    def test_login_page_loads(self, page: Page, base_url):
        page.goto(f"{base_url}/app")
        expect(page.locator('input[type="text"]')).to_be_visible()
        expect(page.locator('input[type="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_login_with_wrong_credentials_shows_error(self, page: Page, base_url):
        page.goto(f"{base_url}/app")
        page.fill('input[type="text"]', "wrong_user")
        page.fill('input[type="password"]', "wrong_password")
        page.click('button[type="submit"]')
        expect(page.locator(".login-error")).to_be_visible(timeout=5000)


class TestNavigation:
    def test_dashboard_loads(self, authenticated_page: Page):
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()
        expect(authenticated_page.locator(".bottom-nav")).to_be_visible()

    def test_navigate_to_shopping(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/shopping"]')
        authenticated_page.wait_for_url("**/app#/shopping", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()

    def test_navigate_to_recipes(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/recipes"]')
        authenticated_page.wait_for_url("**/app#/recipes", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()

    def test_navigate_to_chat(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/chat"]')
        authenticated_page.wait_for_url("**/app#/chat", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()

    def test_navigate_to_profile(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/profile"]')
        authenticated_page.wait_for_url("**/app#/profile", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()


class TestChatFlow:
    def test_chat_input_visible(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/chat"]')
        authenticated_page.wait_for_url("**/app#/chat", timeout=5000)
        expect(authenticated_page.locator("#chat-input")).to_be_visible()
        expect(authenticated_page.locator("#chat-send-btn")).to_be_visible()


class TestTasksFlow:
    def test_tasks_page_loads(self, authenticated_page: Page):
        authenticated_page.goto(f"{authenticated_page.url.split('#')[0]}#/tasks")
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()


class TestProfileFlow:
    def test_profile_shows_user_info(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/profile"]')
        authenticated_page.wait_for_url("**/app#/profile", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()
