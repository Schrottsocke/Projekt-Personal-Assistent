"""Integration-Tests: Notification System CRUD (Events, Preferences, History)."""


class TestNotificationEvents:
    def test_create_event(self, client, auth_headers):
        resp = client.post(
            "/notifications/events",
            json={"type": "reminder", "title": "Test Alert", "channel": "inapp"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "reminder"
        assert data["title"] == "Test Alert"
        assert data["status"] == "new"
        assert data["channel"] == "inapp"

    def test_list_events(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "info", "title": "Event A"},
            headers=auth_headers,
        )
        client.post(
            "/notifications/events",
            json={"type": "warning", "title": "Event B"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_filter_events_by_type(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "unique_type", "title": "Filtered"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events?type=unique_type", headers=auth_headers)
        assert resp.status_code == 200
        assert all(e["type"] == "unique_type" for e in resp.json())

    def test_filter_events_by_channel(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "Push", "channel": "push"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events?channel=push", headers=auth_headers)
        assert resp.status_code == 200
        assert all(e["channel"] == "push" for e in resp.json())

    def test_unread_count(self, client, auth_headers):
        # Create two new events
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "Unread 1"},
            headers=auth_headers,
        )
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "Unread 2"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] >= 2

    def test_update_event_status(self, client, auth_headers):
        create = client.post(
            "/notifications/events",
            json={"type": "test", "title": "To Read"},
            headers=auth_headers,
        )
        event_id = create.json()["id"]

        resp = client.patch(
            f"/notifications/events/{event_id}",
            json={"status": "read"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "read"
        assert resp.json()["read_at"] is not None

    def test_mark_all_read(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "Bulk 1"},
            headers=auth_headers,
        )
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "Bulk 2"},
            headers=auth_headers,
        )
        resp = client.post("/notifications/events/mark-all-read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["marked_read"] >= 2

        # Verify unread count is 0
        count = client.get("/notifications/events/unread-count", headers=auth_headers)
        assert count.json()["unread_count"] == 0

    def test_delete_event(self, client, auth_headers):
        create = client.post(
            "/notifications/events",
            json={"type": "test", "title": "To Delete"},
            headers=auth_headers,
        )
        event_id = create.json()["id"]

        resp = client.delete(f"/notifications/events/{event_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_event(self, client, auth_headers):
        resp = client.delete("/notifications/events/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_nonexistent_event(self, client, auth_headers):
        resp = client.patch(
            "/notifications/events/99999",
            json={"status": "read"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestNotificationHistory:
    def test_history_returns_recent(self, client, auth_headers):
        client.post(
            "/notifications/events",
            json={"type": "test", "title": "History Item"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/history?days=30", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_history_default_30_days(self, client, auth_headers):
        resp = client.get("/notifications/history", headers=auth_headers)
        assert resp.status_code == 200


class TestNotificationPreferences:
    def test_upsert_preference(self, client, auth_headers):
        resp = client.put(
            "/notifications/preferences/finance",
            json={
                "push_enabled": True,
                "email_enabled": False,
                "quiet_start": "22:00",
                "quiet_end": "07:00",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "finance"
        assert data["push_enabled"] is True
        assert data["email_enabled"] is False

    def test_get_preference(self, client, auth_headers):
        client.put(
            "/notifications/preferences/inventory",
            json={"push_enabled": False, "email_enabled": True, "quiet_start": "23:00", "quiet_end": "06:00"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/preferences/inventory", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["push_enabled"] is False

    def test_list_preferences(self, client, auth_headers):
        client.put(
            "/notifications/preferences/cat_a",
            json={"push_enabled": True, "email_enabled": True, "quiet_start": "22:00", "quiet_end": "07:00"},
            headers=auth_headers,
        )
        client.put(
            "/notifications/preferences/cat_b",
            json={"push_enabled": False, "email_enabled": False, "quiet_start": "22:00", "quiet_end": "07:00"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/preferences", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_update_existing_preference(self, client, auth_headers):
        client.put(
            "/notifications/preferences/update_test",
            json={"push_enabled": True, "email_enabled": True, "quiet_start": "22:00", "quiet_end": "07:00"},
            headers=auth_headers,
        )
        resp = client.put(
            "/notifications/preferences/update_test",
            json={"push_enabled": False, "email_enabled": False, "quiet_start": "23:00", "quiet_end": "08:00"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["push_enabled"] is False
        assert resp.json()["quiet_start"] == "23:00"

    def test_delete_preference(self, client, auth_headers):
        client.put(
            "/notifications/preferences/to_delete",
            json={"push_enabled": True, "email_enabled": True, "quiet_start": "22:00", "quiet_end": "07:00"},
            headers=auth_headers,
        )
        resp = client.delete("/notifications/preferences/to_delete", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_preference(self, client, auth_headers):
        resp = client.delete("/notifications/preferences/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_nonexistent_preference(self, client, auth_headers):
        resp = client.get("/notifications/preferences/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestMultiTenancy:
    def test_user_cannot_see_other_users_events(self, client, auth_headers, auth_headers_nina):
        """User A's events should not be visible to User B."""
        client.post(
            "/notifications/events",
            json={"type": "secret", "title": "Taake Only"},
            headers=auth_headers,
        )
        resp = client.get("/notifications/events?type=secret", headers=auth_headers_nina)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_user_cannot_update_other_users_event(self, client, auth_headers, auth_headers_nina):
        """User B should not be able to update User A's event."""
        create = client.post(
            "/notifications/events",
            json={"type": "test", "title": "Taake Event"},
            headers=auth_headers,
        )
        event_id = create.json()["id"]

        resp = client.patch(
            f"/notifications/events/{event_id}",
            json={"status": "read"},
            headers=auth_headers_nina,
        )
        assert resp.status_code == 404


class TestNotificationHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/notifications/health")
        assert resp.status_code == 200
        assert resp.json()["module"] == "notifications"
