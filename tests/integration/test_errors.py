"""Integration-Tests: Error-Cases (401, 404, 422)."""


class TestUnauthorized:
    """Alle geschützten Endpoints geben 401 ohne Token."""

    def test_tasks_401(self, client):
        assert client.get("/tasks").status_code == 401

    def test_shopping_401(self, client):
        assert client.get("/shopping/items").status_code == 401

    def test_dashboard_401(self, client):
        assert client.get("/dashboard/today").status_code == 401

    def test_chat_message_401(self, client):
        assert client.post("/chat/message", json={"message": "hi"}).status_code == 401

    def test_chat_history_401(self, client):
        assert client.get("/chat/history").status_code == 401

    def test_calendar_401(self, client):
        assert client.get("/calendar/today").status_code == 401

    def test_mealplan_401(self, client):
        assert client.get("/meal-plan/week").status_code == 401

    def test_recipes_saved_401(self, client):
        assert client.get("/recipes/saved").status_code == 401


class TestNotFound:
    """404 bei nicht existierenden Ressourcen."""

    def test_task_not_found(self, client, auth_headers):
        resp = client.patch("/tasks/99999", json={"status": "done"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_shopping_item_not_found(self, client, auth_headers):
        resp = client.delete("/shopping/items/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_mealplan_not_found(self, client, auth_headers):
        resp = client.delete("/meal-plan/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_saved_recipe_not_found(self, client, auth_headers):
        resp = client.delete("/recipes/saved/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestValidation:
    """422 bei ungültigen Request-Bodies."""

    def test_login_missing_password(self, client):
        resp = client.post("/auth/login", json={"username": "taake"})
        assert resp.status_code == 422

    def test_task_empty_body(self, client, auth_headers):
        resp = client.post("/tasks", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_chat_missing_message(self, client, auth_headers):
        resp = client.post("/chat/message", json={}, headers=auth_headers)
        assert resp.status_code == 422
