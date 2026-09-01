from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    video_ads_task = route_task(
        "  ViDeO_AdS  ",
        "  制作餐厅短视频广告方案  ",
        "  吉隆坡上班族；午餐套餐 RM15；15 秒竖屏  ",
    )
except ValueError as error:
    raise AssertionError(
        "video_ads 任务必须路由到 Video Ads Agent"
    ) from error

assert isinstance(video_ads_task, TaskBrief)
assert video_ads_task.task_type == "video_ads"
assert video_ads_task.objective == "制作餐厅短视频广告方案"
assert video_ads_task.context == (
    "吉隆坡上班族；午餐套餐 RM15；15 秒竖屏"
)
assert video_ads_task.assigned_agent == "Video Ads Agent"

video_ads_agent = object()
received_requests = []


def run_video_ads(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "开场：午餐选择困难；镜头：套餐特写；"
        "CTA：立即到店。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        video_ads_agent=video_ads_agent,
        run_video_ads=run_video_ads,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Video Ads Agent"
    ) from error

completed = execute_task(video_ads_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Video Ads Agent"
assert completed.output == (
    "开场：午餐选择困难；镜头：套餐特写；"
    "CTA：立即到店。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is video_ads_agent
assert video_ads_task.objective in received_requests[0][1]
assert video_ads_task.context in received_requests[0][1]

print("Video-ads-agent tests passed.")
