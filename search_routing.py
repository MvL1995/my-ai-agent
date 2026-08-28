from datetime import date

SEARCH_PREFIX = "搜索："


def extract_search_query(user_input):
    if not user_input.startswith(SEARCH_PREFIX):
        return None

    return user_input[len(SEARCH_PREFIX):].strip()


def build_search_request(query, current_date=None):
    if current_date is None:
        current_date = date.today().isoformat()

    return (
        f"当前本地日期：{current_date}\n"
        "请使用网页搜索回答，并在答案中列出来源链接："
        f"{query}"
    )