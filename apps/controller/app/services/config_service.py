from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import ProjectConfig


class ConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_configs(self, project_id: int, env_type: Optional[str] = None) -> list:
        query = select(ProjectConfig).where(ProjectConfig.project_id == project_id)
        if env_type:
            query = query.where(ProjectConfig.env_type == env_type)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def set_config(self, project_id: int, env_type: str, config_key: str, config_value: str) -> ProjectConfig:
        result = await self.db.execute(
            select(ProjectConfig).where(
                ProjectConfig.project_id == project_id,
                ProjectConfig.env_type == env_type,
                ProjectConfig.config_key == config_key
            )
        )
        config = result.scalar_one_or_none()
        if config:
            config.config_value = config_value
        else:
            config = ProjectConfig(
                project_id=project_id,
                env_type=env_type,
                config_key=config_key,
                config_value=config_value
            )
            self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_env_config(self, project_id: int, env_type: str) -> Dict[str, str]:
        configs = await self.get_configs(project_id, env_type)
        return {config.config_key: config.config_value for config in configs}

    async def resolve_config(self, project_id: int, env_type: str, keys: list) -> Dict[str, str]:
        env_config = await self.get_env_config(project_id, env_type)
        return {key: env_config.get(key) for key in keys}

    async def delete_config(self, project_id: int, env_type: str, config_key: str) -> bool:
        result = await self.db.execute(
            select(ProjectConfig).where(
                ProjectConfig.project_id == project_id,
                ProjectConfig.env_type == env_type,
                ProjectConfig.config_key == config_key
            )
        )
        config = result.scalar_one_or_none()
        if config:
            await self.db.delete(config)
            await self.db.commit()
            return True
        return False
