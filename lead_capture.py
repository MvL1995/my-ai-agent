import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime
from uuid import uuid4

from memory import DB_PATH


LIMITS = {
    "name": 100,
    "email": 254,
    "company": 100,
    "message": 2000,
    "preferred_time": 50,
    "source_workflow_id": 100,
    "website": 200,
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@contextmanager
def _database():
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            yield conn
    except sqlite3.Error as error:
        raise RuntimeError("Lead storage failed.") from error


def save_lead(payload):
    if not isinstance(payload, dict):
        raise ValueError("Lead body must be an object.")

    lead_id = f"lead-{uuid4().hex}"
    if payload.get("website"):
        return lead_id

    fields = {}
    invalid = []
    for name, limit in LIMITS.items():
        value = payload.get(name, "")
        if not isinstance(value, str) or len(value.strip()) > limit:
            invalid.append(name)
        else:
            fields[name] = value.strip()
    for name in ("name", "email"):
        if not fields.get(name):
            invalid.append(name)
    if invalid:
        raise ValueError(
            "Invalid lead fields: " + ", ".join(dict.fromkeys(invalid))
        )

    if not EMAIL_PATTERN.fullmatch(fields["email"]):
        raise ValueError("Invalid lead email.")

    intent = payload.get("intent")
    if intent not in {"project", "booking"}:
        raise ValueError("Invalid lead intent.")
    if intent == "booking":
        if not fields["preferred_time"]:
            raise ValueError("preferred_time is required for booking.")
        try:
            datetime.fromisoformat(fields["preferred_time"])
        except ValueError as error:
            raise ValueError("Invalid preferred_time.") from error

    is_test = payload.get("is_test", False)
    if not isinstance(is_test, bool):
        raise ValueError("Invalid is_test.")

    with _database() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                lead_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT NOT NULL,
                intent TEXT NOT NULL,
                preferred_time TEXT NOT NULL,
                message TEXT NOT NULL,
                source_workflow_id TEXT NOT NULL,
                is_test INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO leads (
                lead_id, name, email, company, intent, preferred_time,
                message, source_workflow_id, is_test
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                fields["name"],
                fields["email"],
                fields["company"],
                intent,
                fields["preferred_time"],
                fields["message"],
                fields["source_workflow_id"],
                int(is_test),
            ),
        )
    return lead_id
