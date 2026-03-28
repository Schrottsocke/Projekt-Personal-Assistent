"""Integration-Tests: Calendar API."""

from unittest.mock import AsyncMock, MagicMock


class TestCalendar:
    def test_today_not_connected(self, client, auth_headers):
        """Calendar nicht verbunden → connected=False."""
        resp = client.get("/calendar/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["events"] == []

    def test_today_connected(self, client, auth_headers):
        """Calendar verbunden → Events zurückgeben."""
        import api.dependencies as deps

        cal_svc = deps._svc["calendar"]
        cal_svc.is_connected = MagicMock(return_value=True)
        cal_svc.get_todays_events = AsyncMock(
            return_value=[
                {"id": "e1", "summary": "Meeting", "start": "10:00", "end": "11:00"}
            ]
        )

        resp = client.get("/calendar/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert len(data["events"]) == 1
        assert data["events"][0]["summary"] == "Meeting"

    def test_week_not_connected(self, client, auth_headers):
        resp = client.get("/calendar/week", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False

    def test_create_event_not_connected(self, client, auth_headers):
        """Event erstellen ohne verbundenen Calendar → 503."""
        resp = client.post(
            "/calendar/events",
            json={
                "summary": "Test Event",
                "start": "2026-03-30T10:00:00",
                "end": "2026-03-30T11:00:00",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 503
