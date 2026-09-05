import agent_instructions


research_instructions = getattr(
    agent_instructions,
    "RESEARCH_AGENT_INSTRUCTIONS",
    None,
)

assert research_instructions is not None, (
    "Research Agent 专业规范尚未实现"
)


required_guidance = (
    "官方或一手来源",
    "两个独立来源",
    "已验证事实",
    "合理推断",
    "未知信息",
    "行动建议",
    "证据缺口",
    "信息日期",
    "来源链接",
)

for guidance in required_guidance:
    assert guidance in research_instructions

required_labels = (
    "【事实】",
    "【事实｜单一来源】",
    "【推断】",
    "统计口径",
)

for label in required_labels:
    assert label in research_instructions

print("Research-agent-instructions tests passed.")
