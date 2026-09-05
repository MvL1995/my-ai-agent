import json

from input_validation import normalize_user_input

from search_routing import extract_search_query
from search_service import execute_search
from search_cache import SearchCache

from agent_registry import build_agent_handlers
from task_entry import execute_task_request
from workflow_entry import execute_workflow_request
from workflow_history import (
    get_workflow_history,
    get_workflow_run,
    init_workflow_history_db,
)

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
init_workflow_history_db()
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

strategy_agent = Agent(
    name="Strategy Agent",
    instructions=(
        "你是专用营销策略 Agent。"
        "根据任务目标和背景输出可执行策略。"
        "使用中文，包含定位、受众、渠道、信息、"
        "行动步骤和衡量指标。"
        "不要声称完成了未实际执行的研究。"
    ),
)

copywriting_agent = Agent(
    name="Copywriting Agent",
    instructions=(
        "你是专用广告文案 Agent。"
        "根据任务目标和背景撰写可直接使用的中文文案。"
        "输出标题、正文、行动号召和两个可测试变体。"
        "只使用已提供的事实，不虚构效果、数据或承诺。"
    ),
)

web_design_agent = Agent(
    name="Web Design Agent",
    instructions=(
        "你是专用网站体验设计 Agent。"
        "根据任务目标和背景输出可执行的网站设计方案。"
        "使用中文，包含站点结构、页面区块、内容层级、"
        "用户路径、响应式要求和验收标准。"
        "只使用已提供的事实，不虚构素材、数据或研究结论。"
        "除非任务明确要求，否则不要输出代码。"
    ),
)

coding_agent = Agent(
    name="Coding Agent",
    instructions=(
        "你是专用软件开发 Agent。"
        "根据任务目标和技术背景输出最小、可维护的实现。"
        "使用中文说明修改文件、关键代码和验证步骤。"
        "优先复用现有代码和标准库，避免不必要的依赖与抽象。"
        "只依据已提供的项目事实，不声称运行过未实际执行的代码。"
    ),
)

video_ads_agent = Agent(
    name="Video Ads Agent",
    instructions=(
        "你是专用短视频广告策划 Agent。"
        "根据任务目标和背景输出可执行的视频广告制作方案。"
        "使用中文，包含开场钩子、分镜、画面文字、旁白、"
        "行动号召、时长、画幅、素材清单和验收标准。"
        "只使用已提供的事实，不虚构效果、数据或客户素材。"
        "你不直接生成视频，也不要声称已完成拍摄或渲染。"
    ),
)

qa_agent = Agent(
    name="QA Agent",
    instructions=(
        "你是专用质量检查 Agent。"
        "根据任务目标、待检查内容和验收要求进行审查。"
        "使用中文，输出通过或需修改、验收覆盖情况、"
        "关键问题和可执行修改建议。"
        "只检查已提供的内容；缺少证据时标记为未验证。"
        "不要修改原交付物，不要虚构测试结果或声称已发布。"
    ),
)

analytics_agent = Agent(
    name="Analytics Agent",
    instructions=(
        "你是专用数据分析 Agent。"
        "根据任务目标和用户提供的数据进行分析。"
        "使用中文，输出 KPI 摘要、趋势或变化、异常、"
        "数据质量缺口、明确标注的假设，以及优先行动建议。"
        "不要虚构数据、归因或测试结果；缺少必要数据时标记为数据不足。"
        "本阶段不连接或声称访问任何广告平台。"
    ),
)

sales_agent = Agent(
    name="Sales Agent",
    instructions=(
        "你是专用销售支持 Agent。"
        "根据任务目标和客户背景输出可执行的销售方案。"
        "使用中文，包含客户资格判断、价值主张、沟通脚本、"
        "异议处理、跟进步骤和明确的下一行动。"
        "只使用已提供的客户事实，不虚构预算、决策人、案例或成交结果。"
        "你不联系客户、不操作 CRM，也不承诺价格或业务结果。"
    ),
)

client_management_agent = Agent(
    name="Client Project Manager Agent",
    instructions=(
        "你是专用客户与项目管理 Agent。"
        "根据任务目标和项目背景输出可执行的项目管理方案。"
        "使用中文，包含范围、交付物、建议里程碑、负责人、"
        "依赖、风险、客户更新草稿和下一行动。"
        "只使用已提供的项目事实，不虚构进度、承诺或客户决定。"
        "日期和期限必须标记为建议，除非用户已明确确认。"
        "你不发送消息、不修改外部系统，也不保存项目状态。"
    ),
)

task_handlers = build_agent_handlers(
    search_agent,
    cache=search_cache,
    strategy_agent=strategy_agent,
    copywriting_agent=copywriting_agent,
    web_design_agent=web_design_agent,
    coding_agent=coding_agent,
    video_ads_agent=video_ads_agent,
    qa_agent=qa_agent,
    analytics_agent=analytics_agent,
    sales_agent=sales_agent,
    client_management_agent=client_management_agent,
)

main_agent = Agent(
    name="Main Agent",
    instructions=build_instructions,
    tools=[
        remember_memory_tool,
        read_memories_tool,
        forget_memory_tool,
    ],
)

def run_cli():
    print(
        "Loaded project:",
        get_memory("project", "project_name")
    )
    print(read_memories())

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

        if user_input == "查看项目记录":
            runs = get_workflow_history(limit=10)
            print("\n最近客户项目记录：")

            if not runs:
                print("- 暂无项目记录")
            else:
                for run in runs:
                    print(
                        f'- {run["created_at"]} | '
                        f'{run["workflow_id"]} | '
                        f'{run["status"]} | '
                        f'{run["objective"]}'
                    )

            continue

        if user_input.startswith("查看项目详情："):
            workflow_id = user_input.removeprefix(
                "查看项目详情："
            ).strip()

            if not workflow_id:
                print("Main Agent: 请输入工作流 ID。")
                continue

            run = get_workflow_run(workflow_id)

            if run is None:
                print(f"Main Agent: 找不到项目记录：{workflow_id}")
                continue

            print(f'\n项目详情：{run["workflow_id"]}')
            print(f'目标：{run["objective"]}')
            print(f'背景：{run["context"]}')
            print(f'状态：{run["status"]}')
            print("执行步骤：")

            for step in run["steps"]:
                message = step["output"] or step["error"] or ""
                print(
                    f'- {step["agent_name"]} | '
                    f'{step["status"]}：{message}'
                )

            if run["final_output"]:
                print(f'最终结果：{run["final_output"]}')
            elif run["error"]:
                print(f'错误：{run["error"]}')

            continue

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

        try:
            workflow_result = execute_workflow_request(
                user_input,
                task_handlers,
            )
        except (ValueError, RuntimeError) as error:
            print(f"Main Agent: {error}")
            continue

        if workflow_result is not None:
            if workflow_result.status == "completed":
                speaker = "Client Project Workflow"
                message = workflow_result.final_output
            else:
                speaker = "Main Agent"
                message = workflow_result.error

            print(f"\n{speaker}:", message)
            continue

        try:
            task_result = execute_task_request(
                user_input,
                task_handlers,
            )
        except ValueError as error:
            print(f"Main Agent: {error}")
            continue

        if task_result is not None:
            if task_result.status == "completed":
                speaker = task_result.agent_name
                message = task_result.output
            else:
                speaker = "Main Agent"
                message = task_result.error

            print(f"\n{speaker}:", message)
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


if __name__ == "__main__":
    run_cli()
