import importlib.util
import os
import sqlite3
import tempfile
from contextlib import closing


module_spec = importlib.util.find_spec("lead_capture")
assert module_spec is not None, "lead_capture.py 尚未实现"

import lead_capture


original_db_path = lead_capture.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    lead_capture.DB_PATH = os.path.join(temp_dir, "leads.db")
    try:
        lead_id = lead_capture.save_lead({
            "name": "  Test Client  ",
            "email": "client@example.com",
            "company": "  Example Co  ",
            "intent": "booking",
            "preferred_time": "2026-09-10T14:00",
            "message": "  Discuss a landing page.  ",
            "source_workflow_id": "workflow-day085",
            "is_test": True,
            "website": "",
        })
        assert lead_id.startswith("lead-")

        with closing(sqlite3.connect(lead_capture.DB_PATH)) as conn:
            row = conn.execute(
                """
                SELECT name, email, company, intent, preferred_time,
                       message, source_workflow_id, is_test
                FROM leads WHERE lead_id = ?
                """,
                (lead_id,),
            ).fetchone()
        assert row == (
            "Test Client",
            "client@example.com",
            "Example Co",
            "booking",
            "2026-09-10T14:00",
            "Discuss a landing page.",
            "workflow-day085",
            1,
        )

        trapped_id = lead_capture.save_lead({
            "website": "spam.example",
        })
        assert trapped_id.startswith("lead-")
        with closing(sqlite3.connect(lead_capture.DB_PATH)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 1

        invalid_cases = (
            ({"name": " ", "email": "a@b.com", "intent": "project"}, "name"),
            ({"name": "A", "email": "invalid", "intent": "project"}, "email"),
            ({"name": "A", "email": "a@b.com", "intent": "other"}, "intent"),
            ({"name": "A", "email": "a@b.com", "intent": "booking"}, "preferred_time"),
            ({
                "name": "A",
                "email": "a@b.com",
                "intent": "project",
                "message": "x" * 2001,
            }, "message"),
        )
        for payload, field in invalid_cases:
            try:
                lead_capture.save_lead(payload)
            except ValueError as error:
                assert field in str(error)
            else:
                raise AssertionError(f"无效 {field} 必须被拒绝")
        lead_capture.DB_PATH = temp_dir
        try:
            lead_capture.save_lead({
                "name": "A",
                "email": "a@b.com",
                "intent": "project",
            })
        except RuntimeError as error:
            assert str(error) == "Lead storage failed."
        else:
            raise AssertionError("存储故障必须返回受控错误")
    finally:
        lead_capture.DB_PATH = original_db_path

print("Lead-capture tests passed.")
