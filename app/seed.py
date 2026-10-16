import logging

from .db import SessionLocal, init_db
from .models import User
from .security import hash_password

log = logging.getLogger(__name__)

# Pre-created demo accounts so the portal can be tried without signing up.
# New users can also sign up with their own profile and role.
SEED_USERS = [
    {"username": "alice", "full_name": "Alice Rao", "role": "employee", "password": "EmployeePass!123"},
    {"username": "bob", "full_name": "Bob Chen", "role": "employee", "password": "EmployeePass!456"},
    {"username": "priya", "full_name": "Priya Nair", "role": "hr", "password": "HrPass!123"},
    {"username": "sam", "full_name": "Sam Verma", "role": "admin", "password": "AdminPass!123"},
]


def seed_database() -> None:
    init_db()
    with SessionLocal() as db:
        for spec in SEED_USERS:
            if db.query(User).filter(User.username == spec["username"]).first():
                continue
            db.add(
                User(
                    username=spec["username"],
                    full_name=spec["full_name"],
                    role=spec["role"],
                    password_hash=hash_password(spec["password"]),
                )
            )
            log.info("seeded user %s (%s)", spec["username"], spec["role"])
        db.commit()
