"""Integration-Tests: Recipes (Saved Recipes + Chefkoch-Search)."""

import json


class TestRecipesSaved:
    def test_save_recipe(self, client, auth_headers):
        resp = client.post(
            "/recipes/saved",
            json={
                "chefkoch_id": "12345",
                "title": "Test-Rezept",
                "image_url": "https://example.com/img.jpg",
                "servings": 4,
                "prep_time": 15,
                "cook_time": 30,
                "difficulty": "Einfach",
                "ingredients_json": json.dumps([{"name": "Mehl", "amount": "500", "unit": "g"}]),
                "source_url": "https://chefkoch.de/rezepte/12345/",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test-Rezept"
        assert data["chefkoch_id"] == "12345"

    def test_list_saved_recipes(self, client, auth_headers):
        # Rezept speichern
        client.post(
            "/recipes/saved",
            json={
                "chefkoch_id": "67890",
                "title": "Pasta Carbonara",
                "servings": 2,
            },
            headers=auth_headers,
        )

        resp = client.get("/recipes/saved", headers=auth_headers)
        assert resp.status_code == 200
        recipes = resp.json()
        assert len(recipes) >= 1

    def test_toggle_favorite(self, client, auth_headers):
        create = client.post(
            "/recipes/saved",
            json={"chefkoch_id": "fav1", "title": "Favorit-Test", "servings": 4},
            headers=auth_headers,
        )
        recipe_id = create.json()["id"]

        resp = client.patch(f"/recipes/saved/{recipe_id}/favorite", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_favorite"] is True

        # Nochmal togglen → False
        resp = client.patch(f"/recipes/saved/{recipe_id}/favorite", headers=auth_headers)
        assert resp.json()["is_favorite"] is False

    def test_delete_saved_recipe(self, client, auth_headers):
        create = client.post(
            "/recipes/saved",
            json={"chefkoch_id": "del1", "title": "Löschen", "servings": 4},
            headers=auth_headers,
        )
        recipe_id = create.json()["id"]

        resp = client.delete(f"/recipes/saved/{recipe_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_saved(self, client, auth_headers):
        resp = client.delete("/recipes/saved/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestRecipesSearch:
    def test_search_empty_query(self, client, auth_headers):
        resp = client.get("/recipes/search?q=", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_with_query(self, client, auth_headers):
        """Search delegiert an ChefkochService (gemockt)."""
        resp = client.get("/recipes/search?q=pasta", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
