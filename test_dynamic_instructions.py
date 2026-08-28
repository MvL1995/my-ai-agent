import importlib
import importlib.util
import os
import tempfile

import memory


module_spec = importlib.util.find_spec("agent_instructions")

assert module_spec is not None, "agent_instructions.py 尚未实现"

agent_instructions = importlib.import_module("agent_instructions")
builder = getattr(agent_instructions, "build_instructions", None)

assert builder is not None, "build_instructions() 尚未实现"

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()
        memory.save_memory("project", "project_name", "Alpha Studio")
        memory.save_memory("conversation", "preference", "第一版偏好")

        first_instructions = builder(None, None)

        memory.save_memory("conversation", "preference", "第二版偏好")

        second_instructions = builder(None, None)

        assert "第一版偏好" in first_instructions
        assert "第二版偏好" in second_instructions
        assert "第一版偏好" not in second_instructions
    finally:
        memory.DB_PATH = original_db_path

print("Dynamic-instructions tests passed.")