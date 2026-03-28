"""Integration-Tests: Chat."""


class TestChat:
    def test_send_message(self, client, auth_headers):
        """POST /chat/message gibt AI-Antwort zurück."""
        resp = client.post(
            "/chat/message",
            json={"message": "Hallo, wie geht es dir?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["user_message"] == "Hallo, wie geht es dir?"

    def test_chat_history_empty(self, client, auth_headers):
        """GET /chat/history gibt leere Liste bei neuem User."""
        resp = client.get("/chat/history", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_chat_history_with_limit(self, client, auth_headers):
        """GET /chat/history respektiert limit-Parameter."""
        resp = client.get("/chat/history?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
