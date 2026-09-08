import re
import sqlite3
from typing import Literal

DB_PATH = "long_term_memory.db"
MemoryType = Literal[
    "important_memory",
    "preference",
    "goal",
    "fact",
]

MEMORY_TYPE_LABELS = {
    "important_memory": "重要记忆",
    "preference": "偏好",
    "goal": "目标",
    "fact": "事实",
}

SENSITIVE_MEMORY_PATTERN = re.compile(
    r"\bpassword\b|\bapi[\s_-]*key\b|\btoken\b|密码|密钥",
    re.IGNORECASE,
)
SAFE_SENSITIVE_MEMORY_PATTERN = re.compile(
    r"\bno\s+api[\s_-]*key\s+(?:is\s+)?(?:required|needed)\b(?=[.!?;\n]|$)"
    r"|不要(?:保存|记录|存储)?(?:密码|密钥)(?:或(?:密码|密钥))*(?=[。.!！？\n]|$)",
    re.IGNORECASE,
)


def contains_sensitive_memory(content):
    safe_content = SAFE_SENSITIVE_MEMORY_PATTERN.sub("", content)
    return bool(SENSITIVE_MEMORY_PATTERN.search(safe_content))

def extract_memory_command(user_input):
    prefixes = {
        "记住偏好：": "preference",
        "记住目标：": "goal",
        "记住事实：": "fact",
        "记住：": "important_memory",
    }

    for prefix, key in prefixes.items():
        if user_input.startswith(prefix):
            content = user_input[len(prefix):].strip()
            return key, content

    return None

def init_memory_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def record_memory_event(
    action,
    memory_type,
    status
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memory_audit (
            action,
            memory_type,
            status
        )
        VALUES (?, ?, ?)
        """,
        (action, memory_type, status)
    )

    conn.commit()
    conn.close()


def get_memory_audit(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT action, memory_type, status, created_at
        FROM memory_audit
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "action": row[0],
            "memory_type": row[1],
            "status": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]

def save_memory(category, key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM memories
        WHERE category = ? AND key = ?
        """,
        (category, key)
    )

    existing_memory = cursor.fetchone()

    if existing_memory:
        cursor.execute(
            """
            UPDATE memories
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE category = ? AND key = ?
            """,
            (value, category, key)
        )
    else:
        cursor.execute(
            """
            INSERT INTO memories (category, key, value)
            VALUES (?, ?, ?)
            """,
            (category, key, value)
        )

    conn.commit()
    conn.close()


def get_memory(category, key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT value
        FROM memories
        WHERE category = ? AND key = ?
        """,
        (category, key)
    )

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]

    return None

def get_memory_snapshot():
    return {
        memory_type: get_memory(
            "conversation",
            memory_type
        )
        for memory_type in MEMORY_TYPE_LABELS
    }

def delete_memory(category, key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM memories
        WHERE category = ? AND key = ?
        """,
        (category, key)
    )

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted

def remember_memory(
    memory_type: MemoryType,
    content: str
) -> str:
    """Save one explicitly requested long-term memory."""
    if memory_type not in MEMORY_TYPE_LABELS:
        record_memory_event(
            "remember",
            str(memory_type),
            "rejected_type"
        )
        return "不支持的记忆类型。"

    clean_content = content.strip()

    if not clean_content:
        record_memory_event(
            "remember",
            memory_type,
            "rejected_empty"
        )
        return "记忆内容不能为空。"

    if contains_sensitive_memory(clean_content):
        record_memory_event(
            "remember",
            memory_type,
            "rejected_sensitive"
        )
        return (
            "拒绝保存：检测到密码、"
            "API Key、Token 或密钥。"
        )

    save_memory(
        "conversation",
        memory_type,
        clean_content
    )
    record_memory_event(
        "remember",
        memory_type,
        "saved"
    )

    return f"已保存 {memory_type} 长期记忆。"

def read_memories() -> str:
    """Read all allowed long-term memory categories."""
    snapshot = get_memory_snapshot()

    return "\n".join(
        f"{label}: {snapshot[memory_type]}"
        for memory_type, label
        in MEMORY_TYPE_LABELS.items()
    )

def forget_memory(memory_type: MemoryType) -> str:
    """Delete one allowed long-term memory category."""
    if memory_type not in MEMORY_TYPE_LABELS:
        record_memory_event(
            "forget",
            str(memory_type),
            "rejected_type"
        )
        return "不支持的记忆类型。"

    deleted = delete_memory(
        "conversation",
        memory_type
    )

    if deleted:
        record_memory_event(
            "forget",
            memory_type,
            "deleted"
        )
        return f"已删除 {memory_type} 长期记忆。"

    record_memory_event(
        "forget",
        memory_type,
        "not_found"
    )
    return f"{memory_type} 记忆不存在。"

if __name__ == "__main__":
    init_memory_db()

    project_name = get_memory(
        "project",
        "project_name"
    )

    print("Project name:", project_name)