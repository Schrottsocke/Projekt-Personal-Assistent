"""Integration-Tests: Onboarding Flow."""


class TestOnboardingStatus:
    def test_initial_status(self, client, auth_headers):
        resp = client.get("/onboarding/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_onboarded"] is False
        assert data["current_step"] == 0

    def test_profile_step(self, client, auth_headers):
        resp = client.post(
            "/onboarding/profile",
            json={"name": "Taake", "household_size": "couple", "has_side_business": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_step"] >= 1
        assert data["household_size"] == "couple"
        assert data["has_side_business"] is True

    def test_product_lines_step(self, client, auth_headers):
        # First do profile step
        client.post(
            "/onboarding/profile",
            json={"name": "Taake", "household_size": "single"},
            headers=auth_headers,
        )
        resp = client.post(
            "/onboarding/product-lines",
            json={"finance": True, "inventory": True, "family": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_step"] >= 2
        assert data["product_lines"]["finance"] is True
        assert data["product_lines"]["inventory"] is True
        assert data["product_lines"]["family"] is False

    def test_first_action_step(self, client, auth_headers):
        client.post(
            "/onboarding/profile",
            json={"name": "Taake"},
            headers=auth_headers,
        )
        client.post(
            "/onboarding/product-lines",
            json={"finance": True},
            headers=auth_headers,
        )
        resp = client.post(
            "/onboarding/first-action",
            json={"action": "finance"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_step"] >= 3

    def test_dashboard_step(self, client, auth_headers):
        resp = client.post(
            "/onboarding/dashboard",
            json={"widgets": ["notifications", "tasks", "finance"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_step"] >= 4

    def test_complete(self, client, auth_headers):
        # Walk through steps
        client.post("/onboarding/profile", json={"name": "T"}, headers=auth_headers)
        client.post("/onboarding/product-lines", json={"finance": True}, headers=auth_headers)
        client.post("/onboarding/dashboard", json={"widgets": ["tasks"]}, headers=auth_headers)

        resp = client.post("/onboarding/complete", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_onboarded"] is True
        assert data["current_step"] == 5

        # Verify status
        status = client.get("/onboarding/status", headers=auth_headers)
        assert status.json()["is_onboarded"] is True

    def test_restart(self, client, auth_headers):
        # Complete first
        client.post("/onboarding/profile", json={"name": "T"}, headers=auth_headers)
        client.post("/onboarding/complete", headers=auth_headers)

        # Restart
        resp = client.post("/onboarding/restart", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_onboarded"] is False
        assert data["current_step"] == 0


class TestOnboardingHealth:
    def test_health(self, client):
        resp = client.get("/onboarding/health")
        assert resp.status_code == 200
        assert resp.json()["module"] == "onboarding"
