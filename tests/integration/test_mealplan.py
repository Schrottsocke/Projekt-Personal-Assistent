"""Integration-Tests: Meal Plan CRUD."""


class TestMealPlanCRUD:
    def test_add_meal(self, client, auth_headers):
        resp = client.post(
            "/meal-plan",
            json={
                "planned_date": "2026-03-30",
                "recipe_title": "Spaghetti Bolognese",
                "meal_type": "dinner",
                "servings": 4,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["recipe_title"] == "Spaghetti Bolognese"
        assert data["meal_type"] == "dinner"

    def test_get_week(self, client, auth_headers):
        # Eintrag für diese Woche hinzufügen
        client.post(
            "/meal-plan",
            json={
                "planned_date": "2026-03-30",
                "recipe_title": "Salat",
                "meal_type": "lunch",
            },
            headers=auth_headers,
        )

        resp = client.get("/meal-plan/week?start=2026-03-30", headers=auth_headers)
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        assert entries[0]["recipe_title"] == "Salat"

    def test_delete_meal(self, client, auth_headers):
        create = client.post(
            "/meal-plan",
            json={
                "planned_date": "2026-03-31",
                "recipe_title": "Pizza",
                "meal_type": "dinner",
            },
            headers=auth_headers,
        )
        entry_id = create.json()["id"]

        resp = client.delete(f"/meal-plan/{entry_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_meal(self, client, auth_headers):
        resp = client.delete("/meal-plan/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_invalid_date_format(self, client, auth_headers):
        resp = client.get("/meal-plan/week?start=invalid", headers=auth_headers)
        assert resp.status_code == 400
