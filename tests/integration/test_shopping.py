"""Integration-Tests: Shopping CRUD."""


class TestShoppingCRUD:
    def test_add_item(self, client, auth_headers):
        resp = client.post(
            "/shopping/items",
            json={"name": "Milch", "quantity": "1", "unit": "Liter"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Milch"
        assert data["checked"] is False

    def test_list_items(self, client, auth_headers):
        client.post("/shopping/items", json={"name": "Brot"}, headers=auth_headers)
        client.post("/shopping/items", json={"name": "Butter"}, headers=auth_headers)

        resp = client.get("/shopping/items", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 2

    def test_check_item(self, client, auth_headers):
        create = client.post(
            "/shopping/items", json={"name": "Käse"}, headers=auth_headers
        )
        item_id = create.json()["id"]

        resp = client.patch(
            f"/shopping/items/{item_id}",
            json={"checked": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["checked"] is True

    def test_delete_item(self, client, auth_headers):
        create = client.post(
            "/shopping/items", json={"name": "Eier"}, headers=auth_headers
        )
        item_id = create.json()["id"]

        resp = client.delete(f"/shopping/items/{item_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_item(self, client, auth_headers):
        resp = client.delete("/shopping/items/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_clear_checked(self, client, auth_headers):
        # Artikel hinzufügen und abhaken
        create = client.post(
            "/shopping/items", json={"name": "Tomate"}, headers=auth_headers
        )
        item_id = create.json()["id"]
        client.patch(
            f"/shopping/items/{item_id}",
            json={"checked": True},
            headers=auth_headers,
        )

        # Abgehakte löschen
        resp = client.delete("/shopping/items/checked", headers=auth_headers)
        assert resp.status_code == 204

        # Prüfen: keine Items mehr
        resp = client.get("/shopping/items?include_checked=true", headers=auth_headers)
        items = resp.json()
        checked_items = [i for i in items if i["checked"]]
        assert len(checked_items) == 0
