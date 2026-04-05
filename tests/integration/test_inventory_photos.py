"""Integration-Tests: Inventory photo upload, room listing, receipt linking."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

from src.services.database import HouseholdDocument, UserProfile, get_db


def _get_user_id(user_key: str) -> int:
    with get_db()() as db:
        return db.query(UserProfile).filter_by(user_key=user_key).first().id


def _create_household_doc(user_id: int) -> int:
    """Create a HouseholdDocument in the test DB and return its id."""
    with get_db()() as db:
        doc = HouseholdDocument(
            user_id=user_id,
            title="Rechnung Waschmaschine",
            category="receipt",
        )
        db.add(doc)
        db.flush()
        db.refresh(doc)
        return doc.id


class TestUploadItemPhoto:
    def test_upload_photo_to_existing_item(self, client, auth_headers):
        # Create item first
        resp = client.post(
            "/inventory/items",
            json={"name": "Tisch", "room": "Wohnzimmer"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Upload photo
        fake_image = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        with patch(
            "api.routers.inventory_router.StorageService"
        ) as MockStorage:
            instance = MockStorage.return_value
            instance.save = AsyncMock(return_value="taake/2026/04/photo.png")
            resp = client.post(
                f"/inventory/items/{item_id}/photo",
                files={"photo": ("photo.png", fake_image, "image/png")},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item_id
        assert data["photo_url"] == "taake/2026/04/photo.png"

    def test_upload_photo_invalid_type(self, client, auth_headers):
        resp = client.post(
            "/inventory/items",
            json={"name": "Stuhl"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        fake_pdf = BytesIO(b"%PDF-1.4" + b"\x00" * 100)
        resp = client.post(
            f"/inventory/items/{item_id}/photo",
            files={"photo": ("doc.pdf", fake_pdf, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_photo_item_not_found(self, client, auth_headers):
        fake_image = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        resp = client.post(
            "/inventory/items/99999/photo",
            files={"photo": ("photo.png", fake_image, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestRoomListing:
    def test_rooms_returns_distinct_rooms(self, client, auth_headers):
        # Create items in different rooms
        for name, room in [("A", "Kueche"), ("B", "Bad"), ("C", "Kueche"), ("D", "Buero")]:
            client.post(
                "/inventory/items",
                json={"name": name, "room": room},
                headers=auth_headers,
            )

        resp = client.get("/inventory/rooms", headers=auth_headers)
        assert resp.status_code == 200
        rooms = resp.json()["rooms"]
        assert sorted(rooms) == ["Bad", "Buero", "Kueche"]

    def test_rooms_excludes_null_and_empty(self, client, auth_headers):
        client.post(
            "/inventory/items",
            json={"name": "NoRoom"},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "EmptyRoom", "room": ""},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "HasRoom", "room": "Keller"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/rooms", headers=auth_headers)
        assert resp.status_code == 200
        rooms = resp.json()["rooms"]
        assert "Keller" in rooms
        assert "" not in rooms


class TestReceiptLinking:
    def test_link_receipt_to_item(self, client, auth_headers):
        uid = _get_user_id("taake")
        doc_id = _create_household_doc(uid)

        resp = client.post(
            "/inventory/items",
            json={"name": "Waschmaschine", "room": "Keller"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        resp = client.post(
            f"/inventory/items/{item_id}/link-receipt",
            json={"document_id": doc_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["receipt_doc_id"] == doc_id

    def test_link_receipt_document_not_found(self, client, auth_headers):
        resp = client.post(
            "/inventory/items",
            json={"name": "Herd"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        resp = client.post(
            f"/inventory/items/{item_id}/link-receipt",
            json={"document_id": 99999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_link_receipt_item_not_found(self, client, auth_headers):
        uid = _get_user_id("taake")
        doc_id = _create_household_doc(uid)

        resp = client.post(
            "/inventory/items/99999/link-receipt",
            json={"document_id": doc_id},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCreateItemWithPhoto:
    def test_create_with_photo(self, client, auth_headers):
        fake_image = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        with patch(
            "api.routers.inventory_router.StorageService"
        ) as MockStorage:
            instance = MockStorage.return_value
            instance.save = AsyncMock(return_value="taake/2026/04/item.png")
            resp = client.post(
                "/inventory/items-with-photo",
                data={"name": "Lampe", "room": "Flur", "value": "49.99"},
                files={"photo": ("lamp.png", fake_image, "image/png")},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lampe"
        assert data["room"] == "Flur"
        assert data["photo_url"] == "taake/2026/04/item.png"

    def test_create_without_photo(self, client, auth_headers):
        resp = client.post(
            "/inventory/items-with-photo",
            data={"name": "Regal", "room": "Wohnzimmer"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Regal"
        assert data["photo_url"] is None


class TestUserIsolation:
    def test_cannot_access_other_users_item(self, client, auth_headers, auth_headers_nina):
        # taake creates an item
        resp = client.post(
            "/inventory/items",
            json={"name": "Taakes Laptop", "room": "Buero"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        # nina cannot see it
        resp = client.get(f"/inventory/items/{item_id}", headers=auth_headers_nina)
        assert resp.status_code == 404

    def test_cannot_upload_photo_to_other_users_item(self, client, auth_headers, auth_headers_nina):
        resp = client.post(
            "/inventory/items",
            json={"name": "Taakes Kamera"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        fake_image = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        resp = client.post(
            f"/inventory/items/{item_id}/photo",
            files={"photo": ("photo.png", fake_image, "image/png")},
            headers=auth_headers_nina,
        )
        assert resp.status_code == 404

    def test_cannot_link_receipt_to_other_users_item(self, client, auth_headers, auth_headers_nina):
        # taake creates item
        resp = client.post(
            "/inventory/items",
            json={"name": "Taakes Drucker"},
            headers=auth_headers,
        )
        item_id = resp.json()["id"]

        # nina's document
        nina_uid = _get_user_id("nina")
        doc_id = _create_household_doc(nina_uid)

        # nina cannot link to taake's item
        resp = client.post(
            f"/inventory/items/{item_id}/link-receipt",
            json={"document_id": doc_id},
            headers=auth_headers_nina,
        )
        assert resp.status_code == 404
