"""Integration-Tests: Family (Workspaces, Members, Routines)."""


class TestWorkspaces:
    def test_create_workspace(self, client, auth_headers):
        resp = client.post(
            "/family/workspaces",
            json={"name": "Familie Mueller"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Familie Mueller"

    def test_list_workspaces(self, client, auth_headers):
        client.post("/family/workspaces", json={"name": "WS1"}, headers=auth_headers)
        resp = client.get("/family/workspaces", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_workspace_detail(self, client, auth_headers):
        create = client.post("/family/workspaces", json={"name": "Detail WS"}, headers=auth_headers)
        ws_id = create.json()["id"]
        resp = client.get(f"/family/workspaces/{ws_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["workspace"]["name"] == "Detail WS"


class TestMembers:
    def test_add_member(self, client, auth_headers, auth_headers_nina):
        ws = client.post("/family/workspaces", json={"name": "MemberWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        resp = client.post(
            f"/family/workspaces/{ws_id}/members",
            json={"user_key": "nina", "role": "editor"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_remove_member(self, client, auth_headers, auth_headers_nina):
        ws = client.post("/family/workspaces", json={"name": "RemoveWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        add = client.post(
            f"/family/workspaces/{ws_id}/members",
            json={"user_key": "nina", "role": "viewer"},
            headers=auth_headers,
        )
        member_user_id = add.json()["user_id"]
        resp = client.delete(
            f"/family/workspaces/{ws_id}/members/{member_user_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_update_role(self, client, auth_headers, auth_headers_nina):
        ws = client.post("/family/workspaces", json={"name": "RoleWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        add = client.post(
            f"/family/workspaces/{ws_id}/members",
            json={"user_key": "nina", "role": "viewer"},
            headers=auth_headers,
        )
        member_user_id = add.json()["user_id"]
        resp = client.patch(
            f"/family/workspaces/{ws_id}/members/{member_user_id}",
            json={"role": "admin"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_multi_tenancy_workspace_isolation(self, client, auth_headers, auth_headers_nina):
        """User B cannot see User A's workspace unless invited."""
        ws = client.post("/family/workspaces", json={"name": "PrivateWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        # Nina should not see this workspace detail
        resp = client.get(f"/family/workspaces/{ws_id}", headers=auth_headers_nina)
        assert resp.status_code == 403


class TestRoutines:
    def test_create_routine(self, client, auth_headers):
        ws = client.post("/family/workspaces", json={"name": "RoutineWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        resp = client.post(
            f"/family/workspaces/{ws_id}/routines",
            json={"name": "Muell rausbringen", "interval": "weekly"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Muell rausbringen"

    def test_complete_routine(self, client, auth_headers):
        ws = client.post("/family/workspaces", json={"name": "CompleteWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        routine = client.post(
            f"/family/workspaces/{ws_id}/routines",
            json={"name": "Spuelen", "interval": "daily"},
            headers=auth_headers,
        )
        rid = routine.json()["id"]
        resp = client.post(
            f"/family/workspaces/{ws_id}/routines/{rid}/complete",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_routine_rotation(self, client, auth_headers, auth_headers_nina):
        """After completion with rotation strategy, assignee should change."""
        ws = client.post("/family/workspaces", json={"name": "RotationWS"}, headers=auth_headers)
        ws_id = ws.json()["id"]
        # Add nina as member (auth_headers_nina ensures her profile exists)
        client.post(
            f"/family/workspaces/{ws_id}/members",
            json={"user_key": "nina", "role": "editor"},
            headers=auth_headers,
        )
        routine = client.post(
            f"/family/workspaces/{ws_id}/routines",
            json={"name": "Rotation Task", "interval": "daily", "assignee_strategy": "rotation"},
            headers=auth_headers,
        )
        rid = routine.json()["id"]
        initial_assignee = routine.json().get("current_assignee_id")
        # Complete the routine
        client.post(
            f"/family/workspaces/{ws_id}/routines/{rid}/complete",
            json={},
            headers=auth_headers,
        )
        # Check if assignee changed
        resp = client.get(f"/family/workspaces/{ws_id}/routines", headers=auth_headers)
        assert resp.status_code == 200
        updated = [r for r in resp.json() if r["id"] == rid]
        assert len(updated) == 1
        # With rotation and 2 members (owner + nina), assignee should differ
        if initial_assignee is not None:
            assert updated[0]["current_assignee_id"] != initial_assignee


class TestFamilyWidgetSummary:
    def test_family_widget_summary(self, client, auth_headers):
        resp = client.get("/family/widget-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "todays_routines" in data
        assert "workspace_count" in data
