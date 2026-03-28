"""Integration-Tests: Tasks CRUD."""


class TestTasksCRUD:
    def test_create_task(self, client, auth_headers):
        resp = client.post(
            "/tasks",
            json={"title": "Einkaufen gehen", "priority": "high"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Einkaufen gehen"
        assert data["priority"] == "high"
        assert data["status"] == "open"

    def test_list_tasks(self, client, auth_headers):
        # Zwei Tasks erstellen
        client.post("/tasks", json={"title": "Task A"}, headers=auth_headers)
        client.post("/tasks", json={"title": "Task B"}, headers=auth_headers)

        resp = client.get("/tasks", headers=auth_headers)
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) >= 2
        titles = [t["title"] for t in tasks]
        assert "Task A" in titles
        assert "Task B" in titles

    def test_complete_task(self, client, auth_headers):
        # Erstellen
        create_resp = client.post("/tasks", json={"title": "Abschließen"}, headers=auth_headers)
        task_id = create_resp.json()["id"]

        # Abschließen
        resp = client.patch(
            f"/tasks/{task_id}",
            json={"status": "done"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    def test_delete_task(self, client, auth_headers):
        create_resp = client.post("/tasks", json={"title": "Löschen"}, headers=auth_headers)
        task_id = create_resp.json()["id"]

        resp = client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_task(self, client, auth_headers):
        resp = client.delete("/tasks/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_user_isolation(self, client, auth_headers, auth_headers_nina):
        """Tasks eines Users sind für den anderen nicht sichtbar."""
        client.post("/tasks", json={"title": "Taake-Task"}, headers=auth_headers)

        resp = client.get("/tasks", headers=auth_headers_nina)
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()]
        assert "Taake-Task" not in titles
