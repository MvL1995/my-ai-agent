import os
import tempfile

import memory


audit_reader = getattr(
    memory,
    "get_memory_audit",
    None
)

assert audit_reader is not None, (
    "get_memory_audit() 尚未实现"
)

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(
        temp_dir,
        "test_memory.db"
    )

    try:
        memory.init_memory_db()

        memory.remember_memory(
            "preference",
            "我喜欢简洁的中文回答"
        )
        memory.remember_memory(
            "goal",
            "API Key: sk-test-not-real"
        )
        memory.forget_memory("preference")

        events = audit_reader(limit=10)

        event_summary = [
            (
                event["action"],
                event["memory_type"],
                event["status"],
            )
            for event in events
        ]

        assert event_summary == [
            ("forget", "preference", "deleted"),
            ("remember", "goal", "rejected_sensitive"),
            ("remember", "preference", "saved"),
        ]

        assert "sk-test-not-real" not in repr(events)
    finally:
        memory.DB_PATH = original_db_path

print("Memory-audit tests passed.")