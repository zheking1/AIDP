"""统一模型管理服务"""

import json
import logging
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.db.auth_models import AidpModel

logger = logging.getLogger(__name__)


class ModelService:
    """统一模型管理 - 所有工具从 Controller 获取模型配置"""

    # 默认模型配置（首次初始化用）
    DEFAULTS = [
        {
            "name": "DeepSeek Chat",
            "provider": "DeepSeek",
            "model_name": "deepseek-chat",
            "api_base": "https://api.deepseek.com/v1",
            "task_types": ["chat"],
        },
        {
            "name": "DeepSeek Coder",
            "provider": "DeepSeek",
            "model_name": "deepseek-coder",
            "api_base": "https://api.deepseek.com/v1",
            "task_types": ["chat", "code"],
        },
        {
            "name": "text-embedding-3-small",
            "provider": "OpenAI",
            "model_name": "text-embedding-3-small",
            "api_base": "https://api.openai.com/v1",
            "task_types": ["embedding"],
        },
        {
            "name": "all-MiniLM-L6-v2",
            "provider": "Local",
            "model_name": "all-MiniLM-L6-v2",
            "api_base": None,
            "task_types": ["embedding"],
        },
    ]

    @staticmethod
    async def seed_defaults():
        """初始化默认模型"""
        async with async_session_factory() as session:
            count = await session.execute(select(AidpModel))
            if count.scalars().first():
                return
            for m in ModelService.DEFAULTS:
                session.add(AidpModel(**m))
            await session.commit()
            logger.info("Seeded %d default models", len(ModelService.DEFAULTS))

    @staticmethod
    async def list_models() -> List[Dict]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(AidpModel).order_by(AidpModel.priority.desc(), AidpModel.id)
            )
            return [ModelService._to_dict(m) for m in result.scalars().all()]

    @staticmethod
    async def get_by_task(task_type: str) -> List[Dict]:
        """按任务类型获取模型列表"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(AidpModel).where(AidpModel.status == "active").order_by(AidpModel.priority.desc())
            )
            models = result.scalars().all()
            return [
                ModelService._to_dict(m) for m in models
                if task_type in (m.task_types or [])
            ]

    @staticmethod
    async def get_best_for_task(task_type: str) -> Optional[Dict]:
        """获取某个任务的最佳模型（优先级最高的active模型）"""
        models = await ModelService.get_by_task(task_type)
        return models[0] if models else None

    @staticmethod
    async def get_model(model_id: int) -> Optional[Dict]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(AidpModel).where(AidpModel.id == model_id)
            )
            m = result.scalar_one_or_none()
            return ModelService._to_dict(m) if m else None

    @staticmethod
    async def create_model(data: dict) -> Dict:
        async with async_session_factory() as session:
            model = AidpModel(**data)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return ModelService._to_dict(model)

    @staticmethod
    async def update_model(model_id: int, data: dict) -> Optional[Dict]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(AidpModel).where(AidpModel.id == model_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                return None
            for key, value in data.items():
                if value is not None and hasattr(model, key):
                    setattr(model, key, value)
            await session.commit()
            await session.refresh(model)
            return ModelService._to_dict(model)

    @staticmethod
    async def delete_model(model_id: int) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                select(AidpModel).where(AidpModel.id == model_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                return False
            await session.delete(model)
            await session.commit()
            return True

    @staticmethod
    def _to_dict(m: AidpModel) -> Dict:
        return {
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "model_name": m.model_name,
            "api_base": m.api_base,
            "api_key": m.api_key,
            "task_types": m.task_types or [],
            "max_tokens": m.max_tokens or 4096,
            "temperature": m.temperature if m.temperature is not None else 0.7,
            "status": m.status,
            "priority": m.priority,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }


# 公开的查询接口 - 供其他工具调用
async def get_model_for_task(task_type: str) -> Optional[Dict]:
    """获取某个任务类型的模型配置，返回 {'model_name', 'api_base', 'api_key', 'provider'}"""
    return await ModelService.get_best_for_task(task_type)


async def get_all_models_for_task(task_type: str) -> List[Dict]:
    return await ModelService.get_by_task(task_type)