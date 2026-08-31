import json

from input_validation import normalize_user_input

from search_routing import extract_search_query
from search_service import execute_search
from search_cache import SearchCache

from agent_instructions import build_instructions

from session_manager import clear_conversation

from memory import (
    init_memory_db,
    record_memory_event,
    get_memory_audit,
    get_memory,
    delete_memory,
    extract_memory_command,
    remember_memory,
    read_memories,
    forget_memory,
    contains_sensitive_memory,
)

from agents import (
    Agent,
    Runner,
    ModelSettings,
    SQLiteSession,
    ToolGuardrailFunctionOutput,
    function_tool,
    tool_input_guardrail,
    WebSearchTool,
)

init_memory_db()
search_cache = SearchCache(ttl_seconds=300)

@tool_input_guardrail
def protect_sensitive_memory(data):
    arguments = json.loads(
        data.context.tool_arguments
    )
    memory_type = arguments.get(
        "memory_type",
        "unknown"
    )
    content = arguments.get("content", "")

    if contains_sensitive_memory(content):
        record_memory_event(
            "remember",
            memory_type,
            "rejected_sensitive"
        )
        return ToolGuardrailFunctionOutput.reject_content(
            "拒绝保存：检测到密码、API Key、Token 或密钥。"
        )

    return ToolGuardrailFunctionOutput.allow()
remember_memory_tool = function_tool(
    remember_memory,
    tool_input_guardrails=[protect_sensitive_memory]
)

read_memories_tool = function_tool(read_memories)

forget_memory_tool = function_tool(
    forget_memory,
    needs_approval=True
)

web_search_tool = WebSearchTool(
    search_context_size="low"
)

search_agent = Agent(
    name="Search Agent",
    instructions=(
        "你是专用联网搜索 Agent。"
        "必须使用网页搜索后再回答。"
        "使用中文，并在答案末尾列出来源链接。"
    ),
    tools=[web_search_tool],
    model_settings=ModelSettings(
        tool_choice="required"
    ),
)

print(
    "Loaded project:",
    get_memory("project", "project_name")
)
print(read_memories())

main_agent = Agent(
    name="Main Agent",
    instructions=build_instructions,
    tools=[
        remember_memory_tool,
        read_memories_tool,
        forget_memory_tool,
    ],
)

session = SQLiteSession(
    session_id="main_session",
    db_path="agent_memory.db"
)
print("Main Agent 已启动。输入 exit 结束。")

while True:
    raw_input = input("\nYou: ")
    user_input = normalize_user_input(raw_input)

    if user_input is None:
        print("Main Agent: 请输入内容。")
        continue

    if user_input.lower() in ["exit", "quit"]:
        print("Main Agent: 再见！")
        break

    search_query = extract_search_query(user_input)

    if search_query is not None:
        if not search_query:
            print("Main Agent: 请输入搜索内容。")
            continue

        outcome = execute_search(
            search_agent,
            search_query,
            cache=search_cache,
        )

        if outcome["status"] == "completed":
            speaker = "Search Agent"
        else:
            speaker = "Main Agent"

        print(
            f"\n{speaker}:",
            outcome["message"]
        )
        continue

    if user_input == "新对话":
        message = clear_conversation(session)
        print(f"Main Agent: {message}")
        continue

    if user_input == "查看记忆日志":
        events = get_memory_audit(limit=10)
        print("\n最近记忆审计事件：")

        if not events:
            print("- 暂无审计事件")
        else:
            for event in events:
                print(
                    f'- {event["created_at"]} | '
                    f'{event["action"]} | '
                    f'{event["memory_type"]} | '
                    f'{event["status"]}'
                )

        continue

    if user_input == "查看记忆":
        print("\n当前长期记忆：")
        print(
            "- "
            + read_memories().replace(
                "\n",
                "\n- "
            )
        )
        continue

    memory_command = extract_memory_command(user_input)

    if memory_command is not None:
        memory_key, memory_text = memory_command
        message = remember_memory(
            memory_key,
            memory_text
        )
        print(f"Main Agent: {message}")
        continue

    result = Runner.run_sync(
        main_agent,
        user_input,
        session=session 
    )
        	
    if result.interruptions:
        state = result.to_state()

        for interruption in result.interruptions:
            approval = input(
                "\n批准删除？请输入 yes 或 no: "
            ).strip().lower()

            if approval == "yes":
                state.approve(interruption)
            else:
                state.reject(
                    interruption,
                    rejection_message="用户拒绝删除。"
                )

        result = Runner.run_sync(
            main_agent,
            state,
            session=session
        )

    print("\nMain Agent:", result.final_output)
