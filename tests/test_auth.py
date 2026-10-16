from tests.conftest import auth, login


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["documents"] == 12
    assert body["chunks"] > 0


def test_login_success_returns_identity(client):
    response = client.post("/api/auth/login", json={"username": "alice", "password": "EmployeePass!123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "employee"
    assert body["user"]["username"] == "alice"


def test_login_wrong_password(client):
    response = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_unknown_user_gets_generic_error(client):
    response = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_signup_then_login_with_same_password(client):
    signup = client.post(
        "/api/auth/signup",
        json={"full_name": "Neha Gupta", "username": "neha", "password": "NehaPass!123", "role": "hr"},
    )
    assert signup.status_code == 201, signup.text
    assert signup.json() == {"username": "neha", "full_name": "Neha Gupta", "role": "hr"}

    # the exact password chosen at signup works
    token = login(client, "neha", "NehaPass!123")
    me = client.get("/api/auth/me", headers=auth(token)).json()
    assert me["role"] == "hr"

    # a different password fails with a clear error
    wrong = client.post("/api/auth/login", json={"username": "neha", "password": "not-the-password"})
    assert wrong.status_code == 401
    assert "Invalid" in wrong.json()["detail"]


def test_signup_duplicate_username_rejected(client):
    response = client.post(
        "/api/auth/signup",
        json={"full_name": "Fake Alice", "username": "alice", "password": "SomePass!123", "role": "employee"},
    )
    assert response.status_code == 409
    assert "taken" in response.json()["detail"].lower()


def test_signup_validation_errors(client):
    # password too short
    response = client.post(
        "/api/auth/signup",
        json={"full_name": "Short Pass", "username": "shortpass", "password": "abc", "role": "employee"},
    )
    assert response.status_code == 422

    # invalid role
    response = client.post(
        "/api/auth/signup",
        json={"full_name": "Bad Role", "username": "badrole", "password": "GoodPass!123", "role": "developer"},
    )
    assert response.status_code == 422

    # invalid username characters
    response = client.post(
        "/api/auth/signup",
        json={"full_name": "Bad Name", "username": "bad name!", "password": "GoodPass!123", "role": "employee"},
    )
    assert response.status_code == 422


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/chat/history").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage-token")).status_code == 401


def test_account_lockout_after_five_failures(client):
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    with SessionLocal() as db:
        if not db.query(User).filter(User.username == "locky").first():
            db.add(User(username="locky", full_name="Lock Test", role="employee", password_hash=hash_password("LockyPass!123")))
            db.commit()

    for _ in range(5):
        response = client.post("/api/auth/login", json={"username": "locky", "password": "wrong"})
        assert response.status_code in (401, 423)

    # sixth attempt - even with the correct password - must be locked (423)
    response = client.post("/api/auth/login", json={"username": "locky", "password": "LockyPass!123"})
    assert response.status_code == 423
    assert "locked" in response.json()["detail"].lower()


def test_role_in_token_must_match_account(client):
    # tokens are signed; a tampered role claim must be rejected
    import jwt

    from app.config import get_settings

    token = login(client, "alice", "EmployeePass!123")
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    forged = jwt.encode({**payload, "role": "admin"}, get_settings().jwt_secret, algorithm="HS256")
    assert client.get("/api/auth/me", headers=auth(forged)).status_code == 401
