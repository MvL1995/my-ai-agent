import asyncio


def clear_conversation(session):
    asyncio.run(
        session.clear_session()
    )

    return "已开始新对话，长期记忆保持不变。"