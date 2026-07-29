"""
自动分类服务
职责：根据技能/规则内容自动生成 tags、description、建议分组
使用 Intent Analyzer 或 Ranker 角色的小模型
"""
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

import httpx

from app.tools.skill_router.config import settings
from app.tools.skill_router.db.models import LLMConfig, SkillGroup, RuleGroup

logger = logging.getLogger(__name__)


class ClassificationService:
    """
    自动分类服务
    用于技能/规则的自动标签生成、描述生成、分组建议
    """
    
    def __init__(self):
        self._client = None
    
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
    
    async def get_classifier_config(self, db_session) -> Optional[LLMConfig]:
        """
        获取分类器角色的LLM配置
        优先 DB Intent Analyzer → DB Ranker → Controller
        """
        from sqlalchemy import select
        
        try:
            result = await db_session.execute(
                select(LLMConfig)
                .where(LLMConfig.role == "Intent Analyzer")
                .where(LLMConfig.is_healthy == True)
                .where(LLMConfig.is_default == True)
            )
            config = result.scalar_one_or_none()
            if not config:
                result = await db_session.execute(
                    select(LLMConfig)
                    .where(LLMConfig.role == "Ranker")
                    .where(LLMConfig.is_healthy == True)
                    .where(LLMConfig.is_default == True)
                )
                config = result.scalar_one_or_none()
            return config
        except Exception as e:
            logger.error(f"Failed to get classifier config: {e}")
            return None
    
    async def classify_skill(
        self,
        db_session,
        name: str,
        content: str,
        existing_tags: List[str] = None,
        existing_description: str = None,
    ) -> Dict[str, Any]:
        """
        分析技能内容，生成 tags、description、建议分组
        
        Returns:
            {
                "tags": ["tag1", "tag2", ...],
                "description": "技能描述",
                "suggested_group": "建议分组名称",
                "category": "分类"
            }
        """
        config = await self.get_classifier_config(db_session)
        if not config:
            logger.warning("No classifier config available, returning empty classification")
            return {
                "tags": existing_tags or [],
                "description": existing_description or "",
                "suggested_group": None,
                "category": None,
            }
        
        prompt = self._build_skill_classify_prompt(name, content, existing_tags, existing_description)
        
        try:
            response = await self._call_llm(config, prompt)
            if response:
                return self._parse_classification_response(response, existing_tags, existing_description)
        except asyncio.TimeoutError:
            logger.warning("Classifier LLM timeout")
        except Exception as e:
            logger.error(f"Classification error: {e}")
        
        return {
            "tags": existing_tags or [],
            "description": existing_description or "",
            "suggested_group": None,
            "category": None,
        }
    
    async def classify_rule(
        self,
        db_session,
        name: str,
        content: str,
        existing_tags: List[str] = None,
        existing_description: str = None,
    ) -> Dict[str, Any]:
        """
        分析规则内容，生成 tags、description、建议分组
        """
        config = await self.get_classifier_config(db_session)
        if not config:
            logger.warning("No classifier config available")
            return {
                "tags": existing_tags or [],
                "description": existing_description or "",
                "suggested_group": None,
                "category": None,
            }
        
        prompt = self._build_rule_classify_prompt(name, content, existing_tags, existing_description)
        
        try:
            response = await self._call_llm(config, prompt)
            if response:
                return self._parse_classification_response(response, existing_tags, existing_description)
        except asyncio.TimeoutError:
            logger.warning("Classifier LLM timeout")
        except Exception as e:
            logger.error(f"Classification error: {e}")
        
        return {
            "tags": existing_tags or [],
            "description": existing_description or "",
            "suggested_group": None,
            "category": None,
        }
    
    def _build_skill_classify_prompt(
        self,
        name: str,
        content: str,
        existing_tags: List[str] = None,
        existing_description: str = None,
    ) -> str:
        """
        构建技能分类的提示词
        """
        content_preview = content[:500] if len(content) > 500 else content
        
        prompt = f"""请分析以下技能，为其生成合适的分类信息：

技能名称：{name}
技能内容（前500字）：
{content_preview}

当前标签：{existing_tags or "无"}
当前描述：{existing_description or "无"}

请返回以下JSON格式（仅返回JSON，不要其他内容）：
{
    "tags": ["标签1", "标签2", ...],
    "description": "技能的简短描述（不超过100字）",
    "suggested_group": "建议的分组名称",
    "category": "技能分类（如：数据处理、代码生成、文档处理等）"
}

标签要求：
1. 从内容中提取关键技术关键词
2. 标签数量控制在3-5个
3. 使用小写英文或中文
4. 优先使用已有的常见标签：python, javascript, 数据处理, csv, excel, pdf, 文档, 代码生成, 测试, 部署

分组建议：
1. 根据技能功能类型分组
2. 常见分组：数据处理、代码开发、文档管理、测试工具、部署运维
"""
        return prompt
    
    def _build_rule_classify_prompt(
        self,
        name: str,
        content: str,
        existing_tags: List[str] = None,
        existing_description: str = None,
    ) -> str:
        """
        构建规则分类的提示词
        """
        content_preview = content[:500] if len(content) > 500 else content
        
        prompt = f"""请分析以下规则，为其生成合适的分类信息：

规则名称：{name}
规则内容（前500字）：
{content_preview}

当前标签：{existing_tags or "无"}
当前描述：{existing_description or "无"}

请返回以下JSON格式（仅返回JSON，不要其他内容）：
{
    "tags": ["标签1", "标签2", ...],
    "description": "规则的简短描述（不超过100字）",
    "suggested_group": "建议的分组名称",
    "category": "规则分类（如：安全规则、性能规则、业务规则等）"
}

标签要求：
1. 从内容中提取关键规则关键词
2. 标签数量控制在2-4个
3. 使用小写英文或中文
4. 优先使用已有标签：安全、权限、性能、业务逻辑、数据校验

分组建议：
1. 根据规则作用类型分组
2. 常见分组：安全规则、性能规则、业务规则、数据规则
"""
        return prompt
    
    async def _call_llm(self, config: LLMConfig, prompt: str) -> Optional[str]:
        """
        调用LLM API
        """
        try:
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,  # 低温度，更稳定的输出
                "max_tokens": 500,
            }
            
            headers = {
                "Content-Type": "application/json",
            }
            if config.api_key:
                headers["Authorization"] = f"Bearer {config.api_key}"
            
            resp = await self.client.post(
                f"{config.endpoint}/chat/completions",
                json=payload,
                headers=headers,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                logger.warning(f"LLM call failed: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return None
    
    def _parse_classification_response(
        self,
        response: str,
        existing_tags: List[str] = None,
        existing_description: str = None,
    ) -> Dict[str, Any]:
        """
        解析LLM返回的分类结果
        """
        try:
            # 尝试提取JSON
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                result = json.loads(json_str)
                
                # 如果已有tags/description，优先使用用户提供的
                if existing_tags:
                    result["tags"] = existing_tags
                if existing_description:
                    result["description"] = existing_description
                
                return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse classification response: {response}")
        
        return {
            "tags": existing_tags or [],
            "description": existing_description or "",
            "suggested_group": None,
            "category": None,
        }


# 全局单例
classification_service = ClassificationService()


async def analyze_intent_for_retrieval(task: str, instructions: dict = None) -> dict:
    """Stage 1: 分析用户意图，输出 retrieval plan。

    使用模型库的意图分析模型（如果可用），否则使用规则引擎降级。
    只分析 task 和 instructions 的角色/约束部分，不看完整 rules 列表。
    """
    from app.tools.skill_router.db.database import async_session_factory

    intent = {
        "primary": "understand",
        "secondary": None,
        "domain": "general",
        "complexity": "low",
    }
    entities = {"modules": [], "concepts": [], "keywords": []}
    required_tools = ["memory-tool"]
    search_queries = {"memory-tool": []}
    relevant_rules = []
    budget_hints = {"total": 6000, "memory-tool": 6000}

    role = (instructions or {}).get("role", "")
    constraints = (instructions or {}).get("constraints", {})
    rules = (instructions or {}).get("rules", [])

    # Rule-based intent detection
    task_lower = task.lower()
    if any(w in task_lower for w in ("add", "新增", "创建", "implement", "开发")):
        intent["primary"] = "new_feature"
        intent["complexity"] = "medium"
    elif any(w in task_lower for w in ("fix", "修复", "bug", "错误", "修复")):
        intent["primary"] = "bugfix"
        intent["complexity"] = "medium"
    elif any(w in task_lower for w in ("optimize", "优化", "improve", "refactor", "重构")):
        intent["primary"] = "optimize"
        intent["complexity"] = "medium"
    elif any(w in task_lower for w in ("understand", "了解", "分析", "review", "审查")):
        intent["primary"] = "understand"
        intent["complexity"] = "low"

    # Domain detection
    if any(w in task_lower for w in ("sandbox", "sandbox-tool", "沙箱")):
        intent["domain"] = "sandbox-tool"
    elif any(w in task_lower for w in ("knowledge", "knowledge-tool", "知识库")):
        intent["domain"] = "knowledge-tool"
    elif any(w in task_lower for w in ("memory", "memory-tool", "记忆")):
        intent["domain"] = "memory-tool"
    elif any(w in task_lower for w in ("quality", "quality-tool", "质量")):
        intent["domain"] = "quality-tool"
    elif any(w in task_lower for w in ("skill", "skill-router", "技能")):
        intent["domain"] = "skill-router"
    elif any(w in task_lower for w in ("asset", "asset-tool", "资产")):
        intent["domain"] = "asset-tool"
    elif any(w in task_lower for w in ("controller", "编排")):
        intent["domain"] = "controller"
    elif any(w in task_lower for w in ("code-index", "代码索引")):
        intent["domain"] = "code-index"
    elif any(w in task_lower for w in ("deploy", "部署")):
        intent["domain"] = "deploy"

    # Tool selection based on intent
    if intent["primary"] == "new_feature":
        required_tools = ["memory-tool", "knowledge-tool", "code-index"]
    elif intent["primary"] == "bugfix":
        required_tools = ["memory-tool", "code-index", "quality-tool"]
    elif intent["primary"] == "optimize":
        required_tools = ["code-index", "quality-tool", "sandbox-tool"]
    else:
        required_tools = ["memory-tool", "knowledge-tool"]

    # Check constraints for preferred/forbidden tools
    if constraints:
        preferred = constraints.get("preferred_tools", [])
        required_tools = [t for t in required_tools if t in preferred] if preferred else required_tools

    # Extract keyword entities
    keywords = set()
    for word in task.lower().replace(",", " ").replace(".", " ").split():
        word = word.strip()
        if len(word) > 2 and not word.startswith(("-", "的", "在", "和")):
            keywords.add(word)
    entities["keywords"] = list(keywords)[:10]

    # Build search queries
    search_queries = {}
    for tool in required_tools:
        if tool == "memory-tool":
            search_queries[tool] = [intent["domain"], task[:100]]
        elif tool == "knowledge-tool":
            search_queries[tool] = [task[:100]]
        elif tool == "code-index":
            search_queries[tool] = list(keywords)[:5]
        elif tool == "asset-tool":
            search_queries[tool] = [intent["domain"]]
        elif tool == "quality-tool":
            search_queries[tool] = ["check"]
        elif tool == "sandbox-tool":
            search_queries[tool] = ["execute"]

    # Filter relevant rules based on intent domain
    for rule in rules:
        content = rule.get("content", "").lower()
        cat = rule.get("category", "").lower()
        if any(w in content for w in keywords) or intent["domain"] in content or intent["primary"] in cat:
            relevant_rules.append(rule.get("id", ""))

    # Budget allocation
    n_tools = max(len(required_tools), 1)
    per_tool = 6000 // n_tools
    budget_hints = {"total": 6000}
    for tool in required_tools:
        if tool == "code-index":
            budget_hints[tool] = min(per_tool * 2, 4000)
        elif tool == "knowledge-tool":
            budget_hints[tool] = min(per_tool * 2, 4000)
        else:
            budget_hints[tool] = min(per_tool, 2000)

    # Try LLM enhancement if available
    try:
        async with async_session_factory() as session:
            config = await classification_service.get_classifier_config(session)
            if config:
                prompt = f"""Analyze this development task and return a retrieval plan.

Task: {task}
Role: {role}
Domain detected: {intent.get('domain', 'general')}
Intent: {intent.get('primary', 'understand')}

Return JSON with: intent(primary, complexity, domain), entities(modules, concepts, keywords), required_tools(from: memory-tool,knowledge-tool,code-index,asset-tool,sandbox-tool,quality-tool), search_queries(per-tool), relevant_rules, budget_hints(total, per-tool). Keep under 2000 tokens."""  # noqa: E501

                payload = {
                    "model": config.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                }
                headers = {"Content-Type": "application/json"}
                if config.api_key:
                    headers["Authorization"] = f"Bearer {config.api_key}"

                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{config.endpoint}/chat/completions",
                        json=payload, headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if text and "{" in text:
                            try:
                                llm_result = json.loads(text[text.find("{"):text.rfind("}") + 1])
                                if isinstance(llm_result.get("intent"), dict):
                                    intent.update(llm_result.get("intent") or {})
                                if llm_result.get("required_tools"):
                                    required_tools = llm_result["required_tools"]
                                if llm_result.get("search_queries"):
                                    search_queries.update(llm_result.get("search_queries") or {})
                                if llm_result.get("budget_hints"):
                                    budget_hints.update(llm_result.get("budget_hints") or {})
                            except (json.JSONDecodeError, IndexError):
                                pass
    except Exception:
        pass

    return {
        "intent": intent,
        "entities": entities,
        "required_tools": required_tools,
        "search_queries": search_queries,
        "relevant_rules": relevant_rules,
        "budget_hints": budget_hints,
    }