from search_service import execute_search


def build_agent_handlers(
    search_agent,
    cache=None,
    run_search=None,
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

    return {
        "Search Agent": handle_search_task,
    }
