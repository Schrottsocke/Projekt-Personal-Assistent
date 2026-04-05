"""Integration-Tests: Notifications V2 (Events, Preferences)."""


class TestNotificationEvents:
    def test_create_event(self, client, auth_headers):
        resp = client.post(
            "/notifications/events",
            json={
                "type": "reminder",
                "title": "Test Notification",
                "message": "Dies ist ein Test.",
                "channel": "inapp",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["type"] == "reminder"

    def test_list_events(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "Event 1", "message": "Msg 1"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_mark_read(self, client, auth_headers):
        create = client.post(
            "/notifications/events",
            json={"type": "alert", "title": "Unread", "message": "Mark me"},
            headers=auth_headers,
        )
        eid = create.json()["id"]
        resp = client.patch(
            f"/notifications/events/{eid}",
            json={"status": "read"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["read_at"] is not None

    def test_mark_all_read(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "Bulk 1"},
            headers=auth_headers,
        )
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "Bulk 2"},
            headers=auth_headers,
        )
        resp = client.post("/notifications/events/mark-all-read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["marked_read"] >= 2

    def test_unread_count(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "Count Test"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] >= 1

    def test_history_filter(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "History"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/history?days=7", headers=auth_headers)
        assert resp.status_code == 200


class TestNotificationPreferences:
    def test_upsert_preference(self, client, auth_headers):
        resp = client.put(
            "/notifications/preferences/finance",
            json={"push_enabled": True, "email_enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "finance"
        assert resp.json()["email_enabled"] is False

    def test_list_preferences(self, client, auth_headers):
        client.put(
            "/notifications/preferences/testcat",
            json={"push_enabled": True},
            headers=auth_headers,
        )
        resp = client.get("/notifications/preferences", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_preference(self, client, auth_headers):
        client.put(
            "/notifications/preferences/deleteme",
            json={"push_enabled": True},
            headers=auth_headers,
        )
        resp = client.delete("/notifications/preferences/deleteme", headers=auth_headers)
        assert resp.status_code == 204
