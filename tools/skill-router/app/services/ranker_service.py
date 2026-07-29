"""
P1改进：小模型独立重排序服务
与主LLM分离，仅负责技能语义重排序
支持自动降级：API超时/限流 → 跳过重排序
"""
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx

from app.config import settings
from app.db.models import LLMConfig, LLMRoleEnum

logger = logging.getLogger(__name__)


class RankerService:
    """
    小模型重排序服务
    职责：根据用户需求对候选技能列表进行语义重排序
    """
    
    def __init__(self):
        self._client = None
        self._ranker_config = None
    
    @property
    def client(self):
        if self._client is None:
            timeout = settings.llm_timeout or 30
            self._client = httpx.AsyncClient(
                timeout=timeout,
                verify=False,
                follow_redirects=True,
            )
        return self._client
    
    async def get_ranker_config(self, db_session) -> Optional[LLMConfig]:
        """
        获取ranker角色的LLM配置
        优先使用项目级别配置，其次使用全局默认配置
        """
        if self._ranker_config:
            return self._ranker_config
        
        from sqlalchemy import select
        
        try:
            result = await db_session.execute(
                select(LLMConfig)
                .where(LLMConfig.role == "Ranker")
                .where(LLMConfig.is_healthy == True)
                .where(LLMConfig.is_default == True)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                result = await db_session.execute(
                    select(LLMConfig)
                    .where(LLMConfig.role == "Ranker")
                    .where(LLMConfig.is_healthy == True)
                    .limit(1)
                )
                config = result.scalar_one_or_none()
            
            self._ranker_config = config
            return config
        except Exception as e:
            logger.error(f"Failed to get ranker config: {e}")
            return None
    
    async def rerank(
        self,
        db_session,
        user_query: str,
        skills: List[Dict[str, Any]],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        使用小模型对技能列表进行重排序
        
        Args:
            db_session: 数据库会话
            user_query: 用户原始查询
            skills: 候选技能列表（包含id, name, description, content, instruction等）
        
        Returns:
            重排序后的技能列表，包含is_primary标记和新的score
            None表示降级（未使用ranker）
        """
        if not skills:
            return None
        
        config = await self.get_ranker_config(db_session)
        if not config:
            logger.info("No ranker config available, skipping rerank")
            return None
        
        try:
            prompt = self._build_rerank_prompt(user_query, skills)
            response = await self._call_llm(config, prompt)
            
            if response is None:
                logger.info("LLM call failed, skipping rerank")
                return None
            
            return self._parse_rerank_response(response, skills)
        
        except asyncio.TimeoutError:
            logger.warning("Ranker LLM timeout, downgrading to embedding scores")
            return None
        except Exception as e:
            logger.error(f"Ranker error: {e}")
            return None
    
    def _build_rerank_prompt(self, user_query: str, skills: List[Dict[str, Any]]) -> str:
        """
        构建重排序提示词
        优化：增加 examples 字段、更明确的评分标准、更详细的排序逻辑
        """
        skills_text = ""
        for i, skill in enumerate(skills, 1):
            examples = skill.get("examples", []) or []
            examples_text = ""
            if examples:
                examples_text = "\n- Examples:\n" + "\n".join(f"  * {e}" for e in examples[:3])
            
            skills_text += f"""Skill {i}:
- ID: {skill.get('id', '')}
- Name: {skill.get('name', '')}
- Description: {skill.get('description', '')}
- Instruction: {skill.get('instruction', '')}
- Tags: {', '.join(skill.get('tags', []))}
{examples_text}

"""
        
        return f"""You are an expert skill matching assistant. Your task is to rank skills based on how well they can help achieve the user's goal.

User Goal: {user_query}

Available Skills:
{skills_text}

Scoring Criteria (0.0-1.0):
1. Direct Relevance (40%): Does this skill directly address the user's main goal?
   - 1.0: Skill is specifically designed for this exact task
   - 0.7-0.9: Skill can accomplish the task with minor adjustments
   - 0.4-0.6: Skill is somewhat related but not optimal
   - 0.0-0.3: Skill is irrelevant or only tangentially related

2. Instruction Match (30%): How well does the skill's instruction match the user's intent?
   - Check instruction, description, and examples carefully

3. Tag Relevance (20%): Do the skill's tags match keywords in the user's query?

4. Example Match (10%): Do the skill's examples show similar use cases?

Primary Skill Rules:
- Mark is_primary=true only for skills that are ESSENTIAL to achieving the main goal
- At most 2 primary skills allowed
- Secondary skills are supportive/complementary

Output Format (JSON only):
[
  {{
    "skill_id": "<skill_id>",
    "relevance_score": 0.0-1.0,
    "is_primary": true/false,
    "reason": "<brief explanation for this score>"
  }}
]

IMPORTANT: Return ONLY valid JSON, no preamble or extra text."""
    
    async def _call_llm(self, config: LLMConfig, prompt: str) -> Optional[str]:
        """
        调用LLM API
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            }
            
            payload = {
                "model": config.model_name,
                "messages": [
                    {"role": "system", "content": "You are a skill ranking assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
            }
            
            response = await self.client.post(
                config.endpoint + "/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.timeout_secs or 30,
            )
            
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            
            return None
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None
    
    def _parse_rerank_response(self, response: str, original_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析LLM响应并与原始技能列表合并
        """
        try:
            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("Could not find JSON in ranker response")
                return None
            
            ranking_data = json.loads(response[json_start:json_end])
            
            id_to_rank = {item["skill_id"]: item for item in ranking_data}
            
            ranked_skills = []
            for skill in original_skills:
                skill_id = str(skill.get("id", ""))
                rank_info = id_to_rank.get(skill_id)
                
                if rank_info:
                    ranked_skills.append({
                        **skill,
                        "score": rank_info.get("relevance_score", 0),
                        "is_primary": rank_info.get("is_primary", False),
                        "rank_reason": rank_info.get("reason", ""),
                    })
                else:
                    ranked_skills.append(skill)
            
            ranked_skills.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return ranked_skills
        except Exception as e:
            logger.error(f"Failed to parse ranker response: {e}")
            return None
    
    async def health_check(self, db_session) -> Dict[str, Any]:
        """
        健康检查
        """
        config = await self.get_ranker_config(db_session)
        
        if not config:
            return {
                "status": "unavailable",
                "message": "No ranker config found",
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        try:
            test_prompt = "Test ranking"
            test_skills = [{"id": "test-1", "name": "Test", "description": "Test skill", "instruction": "Test"}]
            
            result = await self.rerank(db_session, test_prompt, test_skills)
            
            return {
                "status": "healthy" if result is not None else "degraded",
                "config_name": config.name,
                "model": config.model_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


ranker_service = RankerService()
