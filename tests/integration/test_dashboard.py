"""Integration-Tests: Dashboard."""


class TestDashboard:
    def test_dashboard_today(self, client, auth_headers):
        """Dashboard gibt aggregierte Daten zurück."""
        resp = client.get("/dashboard/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_key"] == "taake"
        assert "events_today" in data
        assert "open_tasks" in data
        assert "shopping_preview" in data
        assert "reminders_today" in data

    def test_dashboard_with_tasks(self, client, auth_headers):
        """Dashboard zeigt vorhandene Tasks."""
        client.post("/tasks", json={"title": "Dashboard-Test"}, headers=auth_headers)

        resp = client.get("/dashboard/today", headers=auth_headers)
        data = resp.json()
        assert data["task_count"] >= 1

    def test_dashboard_calendar_not_connected(self, client, auth_headers):
        """Dashboard zeigt calendar_connected=False wenn nicht verbunden."""
        resp = client.get("/dashboard/today", headers=auth_headers)
        data = resp.json()
        assert data["calendar_connected"] is False
        assert data["events_today"] == []
