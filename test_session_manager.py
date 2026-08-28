import asyncio
import importlib
import importlib.util
import tempfile
from pathlib import Path

from agents import SQLiteSession


module_spec = importlib.util.find_spec(
    "session_manager"
)

assert module_spec is not None, (
    "session_manager.py 尚未实现"
)

session_manager = importlib.import_module(
    "session_manager"
)

clear_conversation = getattr(
    session_manager,
    "clear_conversation",
    None
)

assert clear_conversation is not None, (
    "clear_conversation() 尚未实现"
)

with tempfile.TemporaryDirectory() as temp_dir:
    database_path = (
        Path(temp_dir) / "agent_memory.db"
    )

    session = SQLiteSession(
        session_id="day016_test",
        db_path=database_path
    )

    try:
        asyncio.run(
            session.add_items([
                {
                    "role": "user",
                    "content": "旧聊天内容"
                }
            ])
        )

        before = asyncio.run(
            session.get_items()
        )
        assert len(before) == 1

        message = clear_conversation(session)

        after = asyncio.run(
            session.get_items()
        )

        assert after == []
        assert message == (
            "已开始新对话，长期记忆保持不变。"
        )
    finally:
        session.close()

print("Session-manager tests passed.")