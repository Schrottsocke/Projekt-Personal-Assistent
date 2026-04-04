"""Smoke-Tests: Cross-Modul User Journeys.

Testet die wichtigsten Alltagsflüsse als zusammenhängende Szenarien,
nicht nur isolierte CRUD-Ops. Nutzt TestClient (kein Server nötig).
"""

import json


class TestDashboardFlow:
    """Dashboard: Leerzustand und mit Daten."""

    def test_empty_dashboard(self, client, auth_headers):
        """Frischer User sieht leeres Dashboard ohne Fehler."""
        resp = client.get("/dashboard/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_key"] == "taake"
        assert data["task_count"] == 0
        assert data["events_today"] == []
        assert data["reminders_today"] == []

    def test_dashboard_reflects_created_data(self, client, auth_headers):
        """Tasks und Shopping-Items erscheinen im Dashboard."""
        # Task erstellen
        client.post("/tasks", json={"title": "Dashboard-Smoke"}, headers=auth_headers)
        # Shopping-Item erstellen
        client.post("/shopping/items", json={"name": "Milch"}, headers=auth_headers)

        resp = client.get("/dashboard/today", headers=auth_headers)
        data = resp.json()
        assert data["task_count"] >= 1
        assert len(data["shopping_preview"]) >= 1


class TestTaskLifecycle:
    """Task: Erstellen → Anzeigen → Status ändern → Dashboard prüfen."""

    def test_full_task_lifecycle(self, client, auth_headers):
        # 1. Erstellen
        create = client.post(
            "/tasks",
            json={"title": "Smoke-Task", "priority": "high"},
            headers=auth_headers,
        )
        assert create.status_code == 201
        task_id = create.json()["id"]
        assert create.json()["status"] == "open"

        # 2. In Liste sichtbar
        listing = client.get("/tasks", headers=auth_headers)
        titles = [t["title"] for t in listing.json()]
        assert "Smoke-Task" in titles

        # 3. Status → in_progress
        update1 = client.patch(
            f"/tasks/{task_id}",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert update1.status_code == 200
        assert update1.json()["status"] == "in_progress"

        # 4. Status → done
        update2 = client.patch(
            f"/tasks/{task_id}",
            json={"status": "done"},
            headers=auth_headers,
        )
        assert update2.status_code == 200
        assert update2.json()["status"] == "done"

        # 5. Dashboard: Task-Count reflektiert offene Tasks
        dash = client.get("/dashboard/today", headers=auth_headers)
        # Erledigte Tasks zählen nicht als offen
        open_tasks = [t for t in dash.json().get("open_tasks", []) if t.get("status") != "done"]
        # Kein offener Task mehr (der einzige ist done)
        assert all(t.get("title") != "Smoke-Task" for t in open_tasks)


class TestShoppingLifecycle:
    """Shopping: Hinzufügen → Abhaken → Gecheckte löschen."""

    def test_full_shopping_lifecycle(self, client, auth_headers):
        # 1. Items hinzufügen
        r1 = client.post("/shopping/items", json={"name": "Brot"}, headers=auth_headers)
        r2 = client.post("/shopping/items", json={"name": "Butter"}, headers=auth_headers)
        assert r1.status_code == 201
        assert r2.status_code == 201
        brot_id = r1.json()["id"]

        # 2. Liste prüfen
        listing = client.get("/shopping/items", headers=auth_headers)
        names = [i["name"] for i in listing.json()]
        assert "Brot" in names
        assert "Butter" in names

        # 3. Brot abhaken
        check = client.patch(
            f"/shopping/items/{brot_id}",
            json={"checked": True},
            headers=auth_headers,
        )
        assert check.status_code == 200
        assert check.json()["checked"] is True

        # 4. Gecheckte löschen
        clear = client.delete("/shopping/items/checked", headers=auth_headers)
        assert clear.status_code == 204

        # 5. Nur Butter übrig
        after = client.get("/shopping/items", headers=auth_headers)
        remaining = [i["name"] for i in after.json() if not i["checked"]]
        assert "Butter" in remaining
        assert "Brot" not in remaining


class TestRecipeFlow:
    """Rezept: Speichern → Liste → Favorit → Suche."""

    def test_save_and_favorite_recipe(self, client, auth_headers):
        # 1. Rezept speichern
        create = client.post(
            "/recipes/saved",
            json={
                "chefkoch_id": "smoke-001",
                "title": "Smoke-Pasta",
                "servings": 4,
                "ingredients_json": json.dumps(
                    [
                        {"name": "Nudeln", "amount": "500", "unit": "g"},
                        {"name": "Sahne", "amount": "200", "unit": "ml"},
                    ]
                ),
            },
            headers=auth_headers,
        )
        assert create.status_code == 201
        recipe_id = create.json()["id"]

        # 2. In gespeicherten Rezepten sichtbar
        saved = client.get("/recipes/saved", headers=auth_headers)
        titles = [r["title"] for r in saved.json()]
        assert "Smoke-Pasta" in titles

        # 3. Favorit setzen
        fav = client.patch(f"/recipes/saved/{recipe_id}/favorite", headers=auth_headers)
        assert fav.status_code == 200
        assert fav.json()["is_favorite"] is True

        # 4. Suche funktioniert (gemockter ChefkochService)
        search = client.get("/recipes/search?q=pasta", headers=auth_headers)
        assert search.status_code == 200
        assert isinstance(search.json(), list)


class TestChatFlow:
    """Chat: Nachricht senden → Antwort prüfen, History-Endpoint erreichbar."""

    def test_send_message_returns_response(self, client, auth_headers):
        """Chat-Nachricht wird verarbeitet und AI antwortet."""
        send = client.post(
            "/chat/message",
            json={"message": "Was steht heute an?"},
            headers=auth_headers,
        )
        assert send.status_code == 200
        data = send.json()
        assert data["user_message"] == "Was steht heute an?"
        assert "response" in data
        assert len(data["response"]) > 0

    def test_history_endpoint_works(self, client, auth_headers):
        """History-Endpoint gibt Liste zurück und respektiert Limit."""
        history = client.get("/chat/history", headers=auth_headers)
        assert history.status_code == 200
        assert isinstance(history.json(), list)

        limited = client.get("/chat/history?limit=1", headers=auth_headers)
        assert limited.status_code == 200
        assert len(limited.json()) <= 1

    def test_chat_error_handling(self, client, auth_headers):
        """Leere Nachricht wird mit 422 abgelehnt."""
        resp = client.post("/chat/message", json={}, headers=auth_headers)
        assert resp.status_code == 422


class TestGlobalSearch:
    """Globale Suche: Findet Daten über Module hinweg."""

    def test_search_finds_cross_module_results(self, client, auth_headers):
        # Daten in verschiedenen Modulen erstellen
        client.post("/tasks", json={"title": "Einkaufen gehen"}, headers=auth_headers)
        client.post("/shopping/items", json={"name": "Einkaufstasche"}, headers=auth_headers)

        # Suche nach gemeinsamen Begriff
        resp = client.get("/search?q=Einkauf", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 2

        # Prüfe: Verschiedene Typen in den Ergebnissen
        types = {r["type"] for r in results}
        assert "task" in types
        assert "shopping" in types

        # Jedes Ergebnis hat route-Feld
        for r in results:
            assert r["route"] != ""

    def test_search_empty_result(self, client, auth_headers):
        resp = client.get("/search?q=xyznonexistent999", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_finds_saved_recipes(self, client, auth_headers):
        client.post(
            "/recipes/saved",
            json={"chefkoch_id": "search-001", "title": "Suchrezept Curry", "servings": 2},
            headers=auth_headers,
        )
        resp = client.get("/search?q=Curry", headers=auth_headers)
        results = resp.json()
        recipe_results = [r for r in results if r["type"] == "recipe"]
        assert len(recipe_results) >= 1
        assert "Curry" in recipe_results[0]["title"]


class TestNotificationFlow:
    """Notifications: Erstellen → Liste → Lesen → Bulk → Mark All Read."""

    def test_full_notification_lifecycle(self, client, auth_headers):
        # 1. Notification erstellen
        create = client.post(
            "/notifications",
            json={"type": "system", "title": "Smoke-Test", "message": "Testnachricht"},
            headers=auth_headers,
        )
        assert create.status_code == 201
        notif_id = create.json()["id"]
        assert create.json()["status"] == "new"

        # 2. In Liste sichtbar
        listing = client.get("/notifications", headers=auth_headers)
        assert listing.status_code == 200
        ids = [n["id"] for n in listing.json()]
        assert notif_id in ids

        # 3. Unread-Count > 0
        count = client.get("/notifications/count", headers=auth_headers)
        assert count.json()["unread"] >= 1

        # 4. Als gelesen markieren
        update = client.patch(
            f"/notifications/{notif_id}",
            json={"status": "read"},
            headers=auth_headers,
        )
        assert update.status_code == 200
        assert update.json()["status"] == "read"

    def test_mark_all_read(self, client, auth_headers):
        # Mehrere Notifications erstellen
        client.post(
            "/notifications",
            json={"type": "system", "title": "Bulk-1"},
            headers=auth_headers,
        )
        client.post(
            "/notifications",
            json={"type": "reminder", "title": "Bulk-2"},
            headers=auth_headers,
        )

        # Alle als gelesen markieren
        resp = client.post("/notifications/mark-all-read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] >= 2

        # Count ist jetzt 0
        count = client.get("/notifications/count", headers=auth_headers)
        assert count.json()["unread"] == 0

    def test_bulk_update(self, client, auth_headers):
        r1 = client.post(
            "/notifications",
            json={"type": "system", "title": "Batch-A"},
            headers=auth_headers,
        )
        r2 = client.post(
            "/notifications",
            json={"type": "system", "title": "Batch-B"},
            headers=auth_headers,
        )
        ids = [r1.json()["id"], r2.json()["id"]]

        resp = client.patch(
            "/notifications/bulk",
            json={"ids": ids, "status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2


class TestMultiUserIsolation:
    """Zwei User sehen nur ihre eigenen Daten."""

    def test_tasks_isolated(self, client, auth_headers, auth_headers_nina):
        # Taake erstellt Task
        client.post("/tasks", json={"title": "Taake-Privat"}, headers=auth_headers)

        # Nina sieht ihn nicht
        nina_tasks = client.get("/tasks", headers=auth_headers_nina)
        titles = [t["title"] for t in nina_tasks.json()]
        assert "Taake-Privat" not in titles

    def test_shopping_isolated(self, client, auth_headers, auth_headers_nina):
        # Taake erstellt Shopping-Item
        client.post("/shopping/items", json={"name": "Taake-Milch"}, headers=auth_headers)

        # Nina sieht es nicht
        nina_items = client.get("/shopping/items", headers=auth_headers_nina)
        names = [i["name"] for i in nina_items.json()]
        assert "Taake-Milch" not in names

    def test_notifications_isolated(self, client, auth_headers, auth_headers_nina):
        # Taake erstellt Notification
        client.post(
            "/notifications",
            json={"type": "system", "title": "Taake-Only"},
            headers=auth_headers,
        )

        # Nina sieht sie nicht
        nina_notifs = client.get("/notifications", headers=auth_headers_nina)
        titles = [n["title"] for n in nina_notifs.json()]
        assert "Taake-Only" not in titles

    def test_dashboards_independent(self, client, auth_headers, auth_headers_nina):
        # Taake erstellt Task
        client.post("/tasks", json={"title": "Taake-Dashboard-Task"}, headers=auth_headers)

        # Taake-Dashboard hat Task
        taake_dash = client.get("/dashboard/today", headers=auth_headers)
        assert taake_dash.json()["task_count"] >= 1

        # Nina-Dashboard hat keinen Task
        nina_dash = client.get("/dashboard/today", headers=auth_headers_nina)
        assert nina_dash.json()["task_count"] == 0
