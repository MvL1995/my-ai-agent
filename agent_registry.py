from agents import Runner
from search_service import execute_search


def build_agent_handlers(
    search_agent,
    cache=None,
    run_search=None,
    strategy_agent=None,
    run_strategy=None,
    copywriting_agent=None,
    run_copywriting=None,
    web_design_agent=None,
    run_web_design=None,
    coding_agent=None,
    run_coding=None,
    video_ads_agent=None,
    run_video_ads=None,
    qa_agent=None,
    run_qa=None,
    analytics_agent=None,
    run_analytics=None,
    sales_agent=None,
    run_sales=None,
    client_management_agent=None,
    run_client_management=None,
):
    def handle_search_task(task):
        query = (
            f"{task.objective}\n"
            f"背景：{task.context}"
        )
        outcome = execute_search(
            search_agent,
            query,
            run_search=run_search,
            cache=cache,
        )

        if outcome["status"] != "completed":
            raise RuntimeError(outcome["message"])

        return outcome["message"]

    handlers = {
        "Search Agent": handle_search_task,
    }

    def build_text_agent_handler(agent, run_agent):
        def handle_task(task):
            request = (
                f"目标：{task.objective}\n"
                f"背景：{task.context}"
            )

            if run_agent is not None:
                return run_agent(
                    agent,
                    request,
                )

            result = Runner.run_sync(
                agent,
                request,
            )
            return result.final_output

        return handle_task

    if strategy_agent is not None:
        handlers["Strategy Agent"] = (
            build_text_agent_handler(
                strategy_agent,
                run_strategy,
            )
        )

    if copywriting_agent is not None:
        handlers["Copywriting Agent"] = (
            build_text_agent_handler(
                copywriting_agent,
                run_copywriting,
            )
        )

    if web_design_agent is not None:
        handlers["Web Design Agent"] = (
            build_text_agent_handler(
                web_design_agent,
                run_web_design,
            )
        )

    if coding_agent is not None:
        handlers["Coding Agent"] = (
            build_text_agent_handler(
                coding_agent,
                run_coding,
            )
        )

    if video_ads_agent is not None:
        handlers["Video Ads Agent"] = (
            build_text_agent_handler(
                video_ads_agent,
                run_video_ads,
            )
        )

    if qa_agent is not None:
        handlers["QA Agent"] = (
            build_text_agent_handler(
                qa_agent,
                run_qa,
            )
        )

    if analytics_agent is not None:
        handlers["Analytics Agent"] = (
            build_text_agent_handler(
                analytics_agent,
                run_analytics,
            )
        )

    if sales_agent is not None:
        handlers["Sales Agent"] = (
            build_text_agent_handler(
                sales_agent,
                run_sales,
            )
        )

    if client_management_agent is not None:
        handlers["Client Project Manager Agent"] = (
            build_text_agent_handler(
                client_management_agent,
                run_client_management,
            )
        )

    return handlers
