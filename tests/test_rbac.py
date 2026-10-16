from tests.conftest import auth, login


def test_document_access_matrix(client):
    alice = login(client, "alice", "EmployeePass!123")
    priya = login(client, "priya", "HrPass!123")
    sam = login(client, "sam", "AdminPass!123")

    # employee: leave policy yes, compensation no
    assert client.get("/api/documents/POL-HR-001", headers=auth(alice)).status_code == 200
    assert client.get("/api/documents/POL-HR-002", headers=auth(alice)).status_code == 403

    # hr: compensation yes, access-control (admin-only) no
    assert client.get("/api/documents/POL-HR-002", headers=auth(priya)).status_code == 200
    assert client.get("/api/documents/POL-ADM-002", headers=auth(priya)).status_code == 403

    # admin: access control yes, compensation (hr-only) no
    assert client.get("/api/documents/POL-ADM-002", headers=auth(sam)).status_code == 200
    assert client.get("/api/documents/POL-HR-002", headers=auth(sam)).status_code == 403

    # shared: code of conduct for everyone
    for token in (alice, priya, sam):
        assert client.get("/api/documents/POL-CON-001", headers=auth(token)).status_code == 200


def test_documents_overview_partitions_by_role(client):
    alice = login(client, "alice", "EmployeePass!123")
    body = client.get("/api/documents", headers=auth(alice)).json()
    accessible_ids = {doc["doc_id"] for doc in body["accessible"]}
    restricted_ids = {doc["doc_id"] for doc in body["restricted"]}
    assert "POL-HR-001" in accessible_ids
    assert "POL-HR-002" in restricted_ids
    assert accessible_ids.isdisjoint(restricted_ids)
    assert len(accessible_ids) + len(restricted_ids) == 12


def test_document_denial_is_audited(client):
    alice = login(client, "alice", "EmployeePass!123")
    sam = login(client, "sam", "AdminPass!123")
    client.get("/api/documents/POL-HR-002", headers=auth(alice))  # denied
    audit = client.get("/api/admin/audit?limit=50&decision=deny", headers=auth(sam)).json()
    assert any(row["action"] == "document_denied" and row["actor"] == "alice" for row in audit)


def test_admin_endpoints_require_admin_role(client):
    alice = login(client, "alice", "EmployeePass!123")
    priya = login(client, "priya", "HrPass!123")
    sam = login(client, "sam", "AdminPass!123")
    assert client.get("/api/admin/audit", headers=auth(alice)).status_code == 403
    assert client.get("/api/admin/audit", headers=auth(priya)).status_code == 403
    assert client.get("/api/admin/audit", headers=auth(sam)).status_code == 200
    assert client.get("/api/admin/users", headers=auth(sam)).status_code == 200


def test_records_feature_is_removed(client):
    alice = login(client, "alice", "EmployeePass!123")
    sam = login(client, "sam", "AdminPass!123")
    assert client.get("/api/records/me", headers=auth(alice)).status_code == 404
    assert client.get("/api/records/employees", headers=auth(sam)).status_code == 404


def test_document_view_history_is_per_user(client):
    alice = login(client, "alice", "EmployeePass!123")
    priya = login(client, "priya", "HrPass!123")

    assert client.get("/api/documents/POL-HR-001", headers=auth(alice)).status_code == 200
    assert client.get("/api/documents/POL-EMP-002", headers=auth(alice)).status_code == 200

    history = client.get("/api/documents/history", headers=auth(alice)).json()
    doc_ids = [item["doc_id"] for item in history]
    assert "POL-HR-001" in doc_ids
    assert "POL-EMP-002" in doc_ids
    # most recent view first and titles resolved
    assert doc_ids[0] == "POL-EMP-002"
    assert next(item["title"] for item in history if item["doc_id"] == "POL-HR-001").startswith("Leave")

    # priya's history is separate
    priya_history = client.get("/api/documents/history", headers=auth(priya)).json()
    assert all(item["doc_id"] not in {"POL-EMP-002"} for item in priya_history)
