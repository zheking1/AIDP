"""从 Controller 统一获取模型配置"""

import logging
import httpx
from typing import Optional, Dict

logger = logging.getLogger(__name__)

CONTROLLER_URL = "http://localhost:8883"


async def get_model_for_task(task_type: str) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/api/models/for-task/{task_type}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("model")
    except Exception as e:
        logger.warning("Failed to fetch model for task '%s': %s", task_type, e)
    return None


async def get_chat_model() -> Optional[Dict]:
    return await get_model_for_task("chat")