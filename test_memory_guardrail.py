import memory


checker = getattr(memory, "contains_sensitive_memory", None)

assert checker is not None, "contains_sensitive_memory() 尚未实现"

cases = [
    ("我的密码是 abc123", True),
    ("API Key: sk-test-not-real", True),
    ("token=demo-secret", True),
    ("我喜欢简洁的中文回答", False),
]

for content, expected in cases:
    assert checker(content) is expected

print("Memory-guardrail tests passed.")