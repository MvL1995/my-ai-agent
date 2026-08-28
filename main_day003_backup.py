from memory import save_memory, get_memory, extract_memory_command

from agents import Agent, Runner, SQLiteSession

project_name = get_memory("project", "project_name")
print("Loaded project:", project_name)
important_memory = get_memory("conversation", "important_memory")
print("Important memory:", important_memory)
main_agent = Agent(
    name="Main Agent",
    instructions=f"""
    You are my personal Main AI Agent.

    Known long-term memory:
    - Current project: {project_name}
    - Important memory: {important_memory}

    Your job is to:
    1. Understand what I want to accomplish.
    2. Think about the best way to complete the task.
    3. Use available tools when needed.
    4. Give clear and useful answers.
    5. Ask for clarification only when necessary.

    Always reply in Chinese unless I ask for another language.
    """
)
session = SQLiteSession(
    session_id="main_session",
    db_path="agent_memory.db"
)
print("Main Agent 已启动。输入 exit 结束。")

while True:
    user_input = input("\nYou: ")

    if user_input.lower() in ["exit", "quit"]:
        print("Main Agent: 再见！")
        break

    memory_text = extract_memory_command(user_input)

    if memory_text is not None:
        save_memory("conversation", "important_memory", memory_text)
        print("Main Agent: 已保存长期记忆。")
        continue

    result = Runner.run_sync(
        main_agent,
        user_input,
        session=session 
    )

    print("\nMain Agent:", result.final_output)