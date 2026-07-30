import re
from typing import Optional


def recommend_tags(content: str, filename: Optional[str] = None,
                   content_type: Optional[str] = None) -> dict:
    tags = _extract_tags(content, filename, content_type)
    category = _recommend_category(content, filename, content_type)
    severity = _recommend_severity(content, content_type)

    return {
        "tags": tags,
        "category": category,
        "severity": severity,
    }


_KEYWORD_TAGS = {
    "architecture": ["architecture", "架构", "拓扑", "deployment", "部署"],
    "api": ["api", "接口", "endpoint", "rest", "controller"],
    "database": ["sql", "database", "数据库", "ddl", "migration", "table"],
    "erp": ["erp", "采购", "销售", "库存", "进销存", "采购入库"],
    "security": ["security", "安全", "permission", "权限", "auth"],
    "testing": ["test", "测试", "unit", "integration", "pytest"],
    "devops": ["devops", "docker", "deploy", "ci/cd", "jenkins"],
    "frontend": ["vue", "react", "frontend", "前端", "ui"],
    "backend": ["backend", "后端", "spring", "fastapi", "service"],
    "planning": ["plan", "蓝图", "路线图", "roadmap", "milestone"],
    "business": ["business", "业务", "workflow", "流程"],
    "design": ["design", "设计", "prd", "原型"],
}


def _extract_tags(content: str, filename: Optional[str] = None,
                  content_type: Optional[str] = None) -> list[str]:
    tags: list[str] = []
    text_lower = (content[:5000] + (filename or "")).lower()

    if content_type:
        tags.append(content_type)

    for tag, keywords in _KEYWORD_TAGS.items():
        for kw in keywords:
            if kw in text_lower:
                tags.append(tag)
                break

    tech_stacks = ["python", "java", "typescript", "node", "spring", "fastapi",
                   "vue", "react", "flutter", "docker", "kubernetes", "postgresql",
                   "mysql", "redis", "rabbitmq", "kafka", "nginx"]
    for ts in tech_stacks:
        if ts in text_lower:
            tags.append(ts)

    tags = list(dict.fromkeys(tags))
    return tags[:10]


def _recommend_category(content: str, filename: Optional[str] = None,
                        content_type: Optional[str] = None) -> str:
    text_lower = (content[:2000] + (filename or "")).lower()

    if "adr" in text_lower or "architecture decision" in content[:500].lower():
        return "architecture/adr"
    if "api" in text_lower and ("接口" in text_lower or "endpoint" in text_lower):
        return "api/overview"
    if "sql" in text_lower or "ddl" in text_lower or "create table" in content[:500].lower():
        return "database/schema"
    if "deploy" in text_lower or "docker" in text_lower or "部署" in text_lower:
        return "devops/deployment"
    if "test" in text_lower or "pytest" in text_lower or "vitest" in text_lower:
        return "testing/overview"
    if "erp" in text_lower or "采购" in text_lower:
        return "erp/overview"
    if "架构" in text_lower or "architecture" in text_lower:
        return "architecture/overview"

    if content_type == "rule":
        if "code" in text_lower or "命名" in text_lower:
            return "code_style"
        if "安全" in text_lower or "security" in text_lower:
            return "security"
        return "architecture"

    if content_type == "plan":
        if "erp" in text_lower:
            return "erp/blueprint"
        if "前端" in text_lower or "frontend" in text_lower:
            return "frontend/plan"
        return "planning/general"

    return "uncategorized"


def _recommend_severity(content: str, content_type: Optional[str] = None) -> Optional[str]:
    if content_type != "rule":
        return None

    text_lower = content.lower()

    if re.search(r"severity\s*[=:]\s*critical", text_lower):
        return "critical"
    if re.search(r"severity\s*[=:]\s*high", text_lower):
        return "high"
    if re.search(r"severity\s*[=:]\s*medium", text_lower):
        return "medium"
    if re.search(r"severity\s*[=:]\s*low", text_lower):
        return "low"

    if "critical" in text_lower or "必须" in text_lower:
        return "high"
    if "应当" in text_lower or "建议" in text_lower:
        return "medium"

    return "low"
