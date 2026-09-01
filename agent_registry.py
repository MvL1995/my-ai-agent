from agents import Runner
from search_service import execute_search


def build_agent_handlers(
    search_agent,
    cache=None,
    run_search=None,
    strategy_agent=None,
    run_strategy=None,
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

    if strategy_agent is not None:
        def handle_strategy_task(task):
            request = (
                f"目标：{task.objective}\n"
                f"背景：{task.context}"
            )

            if run_strategy is not None:
                return run_strategy(
                    strategy_agent,
                    request,
                )

            result = Runner.run_sync(
                strategy_agent,
                request,
            )
            return result.final_output

        handlers["Strategy Agent"] = (
            handle_strategy_task
        )

    return handlers
