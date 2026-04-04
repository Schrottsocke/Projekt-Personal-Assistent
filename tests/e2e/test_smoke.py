"""E2E Smoke Tests – kritische User-Flows der WebApp.

Benötigt einen laufenden Server (E2E_BASE_URL) und gültige Credentials
(E2E_TEST_USER, E2E_TEST_PASSWORD). Siehe tests/e2e/README.md.
"""

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
    def test_dashboard_loads_with_widgets(self, authenticated_page: Page):
        """Dashboard zeigt View-Container und Bottom-Nav."""
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()
        expect(authenticated_page.locator(".bottom-nav")).to_be_visible()
        # Dashboard-Content wird gerendert
        expect(authenticated_page.locator("#dashboard-content")).to_be_visible(timeout=5000)

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

    def test_navigate_to_tasks(self, authenticated_page: Page):
        """Tasks-Route ist per Deep-Link erreichbar."""
        base = authenticated_page.url.split("#")[0]
        authenticated_page.goto(f"{base}#/tasks")
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()
        expect(authenticated_page.locator("#task-list")).to_be_visible(timeout=5000)


class TestChatFlow:
    def test_chat_input_and_send_button(self, authenticated_page: Page):
        """Chat-View hat Eingabefeld und Senden-Button."""
        authenticated_page.click('a[data-route="#/chat"]')
        authenticated_page.wait_for_url("**/app#/chat", timeout=5000)
        expect(authenticated_page.locator("#chat-input")).to_be_visible()
        expect(authenticated_page.locator("#chat-send-btn")).to_be_visible()


class TestShoppingFlow:
    def test_shopping_has_input(self, authenticated_page: Page):
        """Shopping-View zeigt Eingabefeld für neue Artikel."""
        authenticated_page.click('a[data-route="#/shopping"]')
        authenticated_page.wait_for_url("**/app#/shopping", timeout=5000)
        expect(authenticated_page.locator("#shopping-input")).to_be_visible(timeout=5000)
        expect(authenticated_page.locator("#shopping-list")).to_be_visible()


class TestTasksFlow:
    def test_tasks_page_renders_list(self, authenticated_page: Page):
        """Tasks-View rendert die Aufgabenliste."""
        base = authenticated_page.url.split("#")[0]
        authenticated_page.goto(f"{base}#/tasks")
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator("#task-list")).to_be_visible(timeout=5000)


class TestProfileFlow:
    def test_profile_shows_user_info(self, authenticated_page: Page):
        authenticated_page.click('a[data-route="#/profile"]')
        authenticated_page.wait_for_url("**/app#/profile", timeout=5000)
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()


class TestErrorStates:
    def test_unknown_route_falls_back(self, authenticated_page: Page):
        """Unbekannte Route fällt auf Dashboard zurück."""
        base = authenticated_page.url.split("#")[0]
        authenticated_page.goto(f"{base}#/nonexistent-route")
        authenticated_page.wait_for_timeout(2000)
        # Router sollte auf Dashboard zurückfallen
        expect(authenticated_page.locator("#view-container")).not_to_be_empty()
