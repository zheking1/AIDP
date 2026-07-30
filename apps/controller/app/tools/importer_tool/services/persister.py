from typing import Optional

import httpx

from app.tools.importer_tool.config import settings


class PersistResult:
    def __init__(self, success: bool, target_type: str, target_id: Optional[str] = None,
                 target_url: Optional[str] = None, version: Optional[int] = None,
                 checksum: Optional[str] = None, skipped: bool = False,
                 error: Optional[str] = None):
        self.success = success
        self.target_type = target_type
        self.target_id = target_id
        self.target_url = target_url
        self.version = version
        self.checksum = checksum
        self.skipped = skipped
        self.error = error

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_url": self.target_url,
            "version": self.version,
            "checksum": self.checksum,
            "skipped": self.skipped,
            "error": self.error,
        }


async def persist_knowledge(title: str, content: str, category: Optional[str] = None,
                            tags: Optional[list[str]] = None, source_uri: Optional[str] = None,
                            user_id: Optional[str] = None) -> PersistResult:
    """POST /api/knowledge/documents — DocumentCreateSimple schema"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            body = {
                "title": title,
                "content": content,
            }
            if category:
                body["category"] = category
            resp = await client.post(
                f"{settings.CONTROLLER_URL}/api/knowledge/documents",
                json=body,
            )
            if resp.status_code == 200:
                data = resp.json()
                return PersistResult(
                    success=True, target_type="knowledge",
                    target_id=data.get("id"),
                    target_url=f"/knowledge/documents/{data.get('id')}",
                    version=1,
                )
            return PersistResult(
                success=False, target_type="knowledge",
                error=f"API returned {resp.status_code}: {resp.text[:200]}",
            )
    except Exception as e:
        return PersistResult(
            success=False, target_type="knowledge",
            error=f"Failed to persist: {str(e)}",
        )


async def persist_skill(name: str, content: str, instruction: Optional[str] = None,
                        scope: str = "personal", tags: Optional[list[str]] = None,
                        user_id: Optional[str] = None) -> PersistResult:
    """POST /api/skills/create — SkillCreate schema"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            body = {
                "name": name,
                "description": "Imported via importer-tool",
                "instruction": instruction or "",
                "content": content,
                "scope": scope,
                "tags": tags or [],
            }
            params = {}
            if scope == "project":
                params["project_id"] = str(user_id) if user_id else "0"
            resp = await client.post(
                f"{settings.CONTROLLER_URL}/api/skills/create",
                params=params,
                json=body,
            )
            if resp.status_code == 200:
                data = resp.json()
                return PersistResult(
                    success=True, target_type="skill",
                    target_id=data.get("id"),
                    target_url=f"/skills/{data.get('id')}",
                    version=data.get("version", 1),
                )
            return PersistResult(
                success=False, target_type="skill",
                error=f"API returned {resp.status_code}: {resp.text[:200]}",
            )
    except Exception as e:
        return PersistResult(
            success=False, target_type="skill",
            error=f"Failed to persist: {str(e)}",
        )


async def persist_rule(name: str, content: str, category: Optional[str] = None,
                       severity: Optional[str] = None, scope: str = "personal",
                       tags: Optional[list[str]] = None,
                       user_id: Optional[str] = None) -> PersistResult:
    """POST /api/rules/create — RuleCreate schema"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            body = {
                "name": name,
                "content": content,
                "category": category or "code_style",
                "severity": severity or "medium",
                "scope": scope,
                "tags": tags or [],
            }
            params = {}
            if scope == "project":
                params["project_id"] = str(user_id) if user_id else "0"
            resp = await client.post(
                f"{settings.CONTROLLER_URL}/api/rules/create",
                params=params,
                json=body,
            )
            if resp.status_code == 200:
                data = resp.json()
                return PersistResult(
                    success=True, target_type="rule",
                    target_id=data.get("id"),
                    target_url=f"/rules/{data.get('id')}",
                    version=1,
                )
            return PersistResult(
                success=False, target_type="rule",
                error=f"API returned {resp.status_code}: {resp.text[:200]}",
            )
    except Exception as e:
        return PersistResult(
            success=False, target_type="rule",
            error=f"Failed to persist: {str(e)}",
        )


async def persist_by_type(content_type: str, title: str, content: str,
                          tags: Optional[list[str]] = None,
                          category: Optional[str] = None,
                          severity: Optional[str] = None,
                          scope: str = "personal",
                          user_id: Optional[str] = None) -> PersistResult:
    if content_type == "knowledge":
        return await persist_knowledge(title, content, category, tags, user_id=user_id)
    elif content_type == "plan":
        plan_tags = (tags or []) + ["plan"]
        return await persist_knowledge(title, content, category, plan_tags, user_id=user_id)
    elif content_type == "skill":
        return await persist_skill(title, content, scope=scope, tags=tags, user_id=user_id)
    elif content_type == "rule":
        return await persist_rule(title, content, category, severity, scope=scope, tags=tags, user_id=user_id)
    else:
        return PersistResult(success=False, target_type=content_type,
                             error=f"Unknown content type: {content_type}")
