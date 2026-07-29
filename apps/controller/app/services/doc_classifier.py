"""
文档智能分类服务
使用 Controller ModelService 的 LLM 对文档进行多维度分类
"""

import json
import logging
from typing import Optional, Dict, Any, List

from app.services.model_service import ModelService

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """你是一个文档分析专家。请分析以下文档内容，返回 JSON 格式的分类结果。

分析维度：
1. doc_type: 文档类型，可选值：
   - "document" - 普通知识文档（README、教程、架构说明、用户指南）
   - "rule" - 规则约束（包含必须/禁止/不得等约束性条款）
   - "skill" - 技能定义（instruction+content 格式的能力描述）
   - "agent" - Agent 定义（角色、指令、行为描述）
   - "standard" - 规范标准（编码规范、API规范、设计规范，兼具文档和规则属性）

2. category: 内容类别，可选值：
   - "architecture" - 架构设计
   - "api" - 接口文档
   - "database" - 数据库
   - "deployment" - 部署运维
   - "security" - 安全
   - "testing" - 测试
   - "devops" - DevOps/CICD
   - "frontend" - 前端
   - "backend" - 后端
   - "business" - 业务
   - "planning" - 规划计划
   - "code_style" - 编码规范
   - "uncategorized" - 未分类

3. level: 适用层级：
   - "framework" - 框架级（技术栈通用，如 Spring Boot 文档）
   - "project" - 项目级（特定项目特有）
   - "template" - 模板级（通用模板）

4. tech_stack: 关联技术栈列表（数组），从文档内容中识别，如 ["Spring Boot", "React", "FastAPI"]

5. tags: 标签列表（数组），概括文档关键词

6. summary: 一句话摘要

7. confidence: 分类置信度 "high" / "medium" / "low"

如果 doc_type 为 "rule"，额外提取：
8. severity: "critical" / "high" / "medium" / "low"
9. scope: "global" / "project" / "personal"

如果 doc_type 为 "agent"，额外提取：
10. role: Agent 角色描述
11. has_instructions: 是否包含具体指令（true/false）

如果 doc_type 为 "standard"，额外提取：
12. has_rules: 是否包含可提取的约束规则（true/false）

请仅返回 JSON，不要加任何其他文字。
```json
{
  "doc_type": "...",
  "category": "...",
  "level": "...",
  "tech_stack": ["..."],
  "tags": ["..."],
  "summary": "...",
  "confidence": "..."
}
```"""


class DocClassifier:
    """文档分类器 - 使用 LLM 分析文档内容"""

    @staticmethod
    async def classify(title: str, content: str, filename: str = "") -> Dict[str, Any]:
        model = await ModelService.get_best_for_task("chat")
        if not model:
            logger.warning("No chat model available, falling back to rule-based classification")
            return DocClassifier._rule_based_fallback(title, content, filename)

        text_for_classify = f"文件名: {filename}\n标题: {title}\n内容:\n{content[:4000]}"

        try:
            result = await DocClassifier._call_llm(model, text_for_classify)
            if result and "doc_type" in result:
                return result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

        return DocClassifier._rule_based_fallback(title, content, filename)

    @staticmethod
    async def _call_llm(model: Dict, text: str) -> Optional[Dict]:
        api_base = model.get("api_base", "").rstrip("/")
        model_name = model.get("model_name", "")
        api_key = model.get("api_key", "")

        if not api_base or not api_key or not model_name:
            logger.warning(f"Incomplete model config: provider={model.get('provider')}")
            return None

        import httpx

        messages = [
            {"role": "system", "content": CLASSIFICATION_PROMPT},
            {"role": "user", "content": text},
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning(f"LLM API error {resp.status_code}: {resp.text[:200]}")
                    return None

                data = resp.json()
                raw = data["choices"][0]["message"]["content"]

                json_start = raw.find("{")
                json_end = raw.rfind("}")
                if json_start >= 0 and json_end > json_start:
                    raw = raw[json_start : json_end + 1]

                result = json.loads(raw)
                return result

        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None

    @staticmethod
    def _rule_based_fallback(title: str, content: str, filename: str) -> Dict[str, Any]:
        content_lower = (content or "").lower()
        title_lower = (title or "").lower()
        filename_lower = (filename or "").lower()

        # Detect rule: constraint keywords
        rule_keywords = ["必须", "禁止", "不得", "应当", "严禁", "severity:", "constraint"]
        if any(kw in content for kw in rule_keywords):
            severity = "medium"
            if any(kw in content_lower for kw in ["critical", "必须", "严禁"]):
                severity = "critical"
            elif any(kw in content_lower for kw in ["high", "禁止"]):
                severity = "high"
            elif any(kw in content_lower for kw in ["low", "建议"]):
                severity = "low"
            return {
                "doc_type": "rule",
                "category": "code_style",
                "level": "project",
                "tech_stack": [],
                "tags": ["rule"],
                "summary": title or "规则约束",
                "confidence": "medium",
                "severity": severity,
                "scope": "project",
            }

        # Detect skill: has instruction + content
        if "instruction:" in content_lower and ("content:" in content_lower or "执行" in content):
            return {
                "doc_type": "skill",
                "category": "uncategorized",
                "level": "project",
                "tech_stack": [],
                "tags": ["skill"],
                "summary": title or "技能定义",
                "confidence": "medium",
            }

        # Detect agent: role description
        agent_keywords = ["agent", "角色", "扮演", "你是一个", "you are a", "role:"]
        if any(kw in content_lower for kw in agent_keywords):
            return {
                "doc_type": "agent",
                "category": "uncategorized",
                "level": "project",
                "tech_stack": [],
                "tags": ["agent"],
                "summary": title or "Agent 定义",
                "confidence": "medium",
                "role": "",
                "has_instructions": "instruction" in content_lower or "指令" in content,
            }

        # Detect standard
        standard_keywords = ["规范", "标准", "规约", "convention", "standard", "guideline"]
        if any(kw in content_lower for kw in standard_keywords):
            return {
                "doc_type": "standard",
                "category": "code_style",
                "level": "project",
                "tech_stack": [],
                "tags": ["standard"],
                "summary": title or "规范文档",
                "confidence": "medium",
                "has_rules": any(kw in content for kw in rule_keywords),
            }

        # Default: document
        # Try to detect category from keywords
        category = "uncategorized"
        cat_map = {
            "architecture": ["架构", "architecture", "设计", "design", "component"],
            "api": ["api", "接口", "endpoint", "rest", "graphql"],
            "database": ["数据库", "database", "sql", "schema", "表结构"],
            "deployment": ["部署", "deploy", "运维", "docker", "kubernetes", "k8s"],
            "security": ["安全", "security", "认证", "鉴权", "oauth", "jwt"],
            "testing": ["测试", "test", "unit", "integration", "e2e"],
            "devops": ["ci/cd", "devops", "pipeline", "github action", "jenkins"],
            "frontend": ["前端", "frontend", "vue", "react", "angular", "ui"],
            "backend": ["后端", "backend", "server", "service"],
            "planning": ["计划", "plan", "路线图", "roadmap", "milestone"],
        }
        for cat, keywords in cat_map.items():
            if any(kw in content_lower for kw in keywords):
                category = cat
                break

        return {
            "doc_type": "document",
            "category": category,
            "level": "project",
            "tech_stack": [],
            "tags": [],
            "summary": title or "未知文档",
            "confidence": "low",
        }