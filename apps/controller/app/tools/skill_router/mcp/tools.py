import hashlib
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.skill_router.config import settings
from app.tools.skill_router.db.database import async_session_factory
from app.tools.skill_router.db.models import User, ApiKey
from app.tools.skill_router.services import skill_service, rule_service
from app.tools.skill_router.services import evolution_service, review_service, model_service
from app.tools.skill_router.services.cache_service import delete_cache
from app.tools.skill_router.services.review_service import pre_review as pre_review_svc
from app.tools.skill_router.services.vector_service import detect_embedding_dim
from app.tools.skill_router.services.resolve_service import resolve_skills
from app.tools.skill_router.services.validation_service import validate_resolve_result
from app.tools.skill_router.services.classification_service import classification_service


def ok(data=None, msg="ok", trace_id: str = ""):
    return {"success": True, "code": "OK", "msg": msg, "data": data or {}, "trace_id": trace_id or str(uuid.uuid4())}


def fail(code: str, msg: str, trace_id: str = ""):
    return {"success": False, "code": code, "msg": msg, "data": {}, "trace_id": trace_id or str(uuid.uuid4())}


async def _resolve_user(api_key: str = None) -> Optional[User]:
    if not api_key:
        api_key = settings.skill_manager_api_key
    if not api_key:
        return None
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    async with async_session_factory() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        )
        ak = result.scalar_one_or_none()
        if ak:
            return await session.get(User, ak.user_id)
    return None


async def _get_user_id(api_key: str = None) -> Optional[UUID]:
    user = await _resolve_user(api_key)
    return user.id if user else None


async def _auto_create_skill_group(session, user_id: UUID, group_name: str) -> UUID:
    """
    自动创建技能分组（如果不存在）
    """
    from app.tools.skill_router.db.models import SkillGroup
    
    # 查找现有分组
    result = await session.execute(
        select(SkillGroup)
        .where(SkillGroup.user_id == user_id)
        .where(SkillGroup.name == group_name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing.id
    
    # 创建新分组
    new_group = SkillGroup(
        name=group_name,
        user_id=user_id,
        sort_order=0,
    )
    session.add(new_group)
    await session.commit()
    await session.refresh(new_group)
    return new_group.id


async def _auto_create_rule_group(session, user_id: UUID, group_name: str) -> UUID:
    """
    自动创建规则分组（如果不存在）
    """
    from app.tools.skill_router.db.models import RuleGroup
    
    # 查找现有分组
    result = await session.execute(
        select(RuleGroup)
        .where(RuleGroup.user_id == user_id)
        .where(RuleGroup.name == group_name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing.id
    
    # 创建新分组
    new_group = RuleGroup(
        name=group_name,
        user_id=user_id,
        sort_order=0,
    )
    session.add(new_group)
    await session.commit()
    await session.refresh(new_group)
    return new_group.id


async def register_mcp_tools(mcp_server):
    tid = str(uuid.uuid4())

    @mcp_server.tool()
    async def resolve_task(
        task: str,
        mode: str = "auto",
        hint_tags: list = None,
        top_k: int = 5,
        no_cache: bool = False,
        exclude_skill_ids: list = None,
        exclude_tags: list = None,
        role: str = None,
        session_id: str = "",
        api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            result = await resolve_skills(
                session=session,
                task=task,
                user_id=user_id,
                mode=mode,
                hint_tags=hint_tags or [],
                top_k=top_k,
                exclude_skill_ids=[UUID(x) for x in exclude_skill_ids] if exclude_skill_ids else None,
                exclude_tags=exclude_tags,
                role=role,
            )
            result["session_context"] = {"session_id": session_id, "task": task} if session_id else None
            
            # P2: 后置校验 - 参数、权限、业务规则校验
            result = validate_resolve_result(result)
            
            return ok(result, trace_id=tid)

    @mcp_server.tool()
    async def skill_register(
        name: str,
        content: str,
        tags: list = None,
        dependencies: list = None,
        description: str = None,
        group_name: str = None,
        auto_classify: bool = True,
        api_key: str = None,
    ) -> dict:
        """
        注册新技能
        
        Args:
            name: 技能名称
            content: 技能内容/代码
            tags: 标签列表（可选，自动分类时会自动生成）
            dependencies: 依赖的技能ID列表
            description: 技能描述（可选，自动分类时会自动生成）
            group_name: 分组名称（可选，自动分类时会自动创建）
            auto_classify: 是否启用自动分类（默认True）
            api_key: API密钥
        """
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        
        async with async_session_factory() as session:
            # 自动分类逻辑
            auto_tags = tags
            auto_desc = description
            auto_group_id = None
            
            if auto_classify and (not tags or not description):
                classification = await classification_service.classify_skill(
                    session, name, content,
                    existing_tags=tags,
                    existing_description=description,
                )
                auto_tags = classification.get("tags", tags or [])
                auto_desc = classification.get("description", description or "")
                suggested_group = classification.get("suggested_group")
                
                # 如果没有指定分组，使用建议的分组
                if not group_name and suggested_group:
                    group_name = suggested_group
            
            # 自动创建分组
            if group_name:
                auto_group_id = await _auto_create_skill_group(session, user_id, group_name)
            
            skill = await skill_service.create_skill(
                session, user_id, name, content, auto_tags, dependencies,
            )
            
            # 更新描述和分组
            if auto_desc or auto_group_id:
                from app.tools.skill_router.db.models import Skill
                skill = await session.get(Skill, skill.id)
                if auto_desc:
                    skill.description = auto_desc
                if auto_group_id:
                    skill.group_id = auto_group_id
                await session.commit()
            
            return ok({
                "id": str(skill.id),
                "tags": auto_tags,
                "description": auto_desc,
                "group_id": str(auto_group_id) if auto_group_id else None,
                "group_name": group_name,
            }, trace_id=tid)

    @mcp_server.tool()
    async def skill_update(id: str, api_key: str = None, name: str = None, description: str = None, content: str = None, tags: str = None, review_status: str = None, review_report: str = None, is_active: bool = None, dependencies: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        dep_list = [d.strip() for d in dependencies.split(",")] if dependencies else None
        async with async_session_factory() as session:
            skill = await skill_service.update_skill(session, UUID(id), name=name, description=description, content=content, tags=tag_list, review_status=review_status, review_report=review_report, is_active=is_active, dependencies=dep_list)
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {id}", tid)
            return ok({"id": str(skill.id), "version": skill.version}, trace_id=tid)

    @mcp_server.tool()
    async def skill_delete(id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            ok_ = await skill_service.delete_skill(session, UUID(id))
            return ok(msg="deleted") if ok_ else fail("NOT_FOUND", f"skill not found: {id}", tid)

    @mcp_server.tool()
    async def skill_get(id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from sqlalchemy.orm import selectinload
            from app.tools.skill_router.db.models import Skill
            result = await session.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == UUID(id)))
            skill = result.scalars().first()
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {id}", tid)
            data = {
                "id": str(skill.id), "name": skill.name, "content": skill.content,
                "tags": skill.tags, "version": skill.version,
                "review_status": skill.review_status,
                "dependencies": [str(d) for d in (skill.dependencies or [])],
                "exec_config": skill.exec_config or {},
                "files": [{"path": f.path, "content": f.content, "language": f.language, "is_entry": f.is_entry} for f in skill.files],
            }
            return ok(data, trace_id=tid)

    @mcp_server.tool()
    async def skill_get_script(id: str, api_key: str = None) -> dict:
        """Get the entry executable script content for a skill (for CLI execution)."""
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from sqlalchemy.orm import selectinload
            from app.tools.skill_router.db.models import Skill
            result = await session.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == UUID(id)))
            skill = result.scalars().first()
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {id}", tid)
            exec_cfg = skill.exec_config or {}
            entry = exec_cfg.get("entry", "")
            entry_file = None
            content = skill.content
            if entry:
                for f in skill.files:
                    if f.path == entry:
                        entry_file = f
                        content = f.content
                        break
            else:
                for f in skill.files:
                    if f.is_entry:
                        entry_file = f
                        content = f.content
                        break
            return ok({
                "id": str(skill.id),
                "name": skill.name,
                "version": skill.version,
                "entry": entry_file.path if entry_file else "",
                "language": entry_file.language if entry_file else "text",
                "content": content,
                "runtime": exec_cfg.get("runtime", "python3"),
                "cmd_template": exec_cfg.get("cmd_template", ""),
                "timeout_secs": exec_cfg.get("timeout_secs", 60),
                "auto_update": exec_cfg.get("auto_update", True),
                "params": exec_cfg.get("params", {}),
                "instruction": skill.instruction or None,
                "project_instruction": skill.project.instruction if skill.project and skill.project.instruction else None,
            }, trace_id=tid)

    @mcp_server.tool()
    async def skill_run(task: str, mode: str = "auto", hint_tags: list = None, top_k: int = 5, role: str = None, session_id: str = None, api_key: str = None) -> dict:
        """Resolve a task to find matching skills and return them with instructions for agent context assembly."""
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.services.resolve_service import resolve_skills
            result = await resolve_skills(
                session=session, task=task, user_id=user_id,
                mode=mode, hint_tags=hint_tags or [], top_k=top_k, role=role,
            )
            skills_out = []
            for s in result.get("skills", []):
                skills_out.append({
                    "id": s["id"],
                    "name": s["name"],
                    "content": s["content"],
                    "instruction": s.get("instruction"),
                    "project_instruction": s.get("project_instruction"),
                    "tags": s.get("tags", []),
                    "score": s.get("score", 0),
                    "sensitive": s.get("sensitive", False),
                    "review_status": s.get("review_status", "pending"),
                    "allowed_roles": s.get("allowed_roles", None),
                })
            validation = result.get("validation", {})
            
            # P0: 增强校验信息返回
            enhanced_validation = {
                "sensitive_skills": validation.get("sensitive_skills", []),
                "output_warnings": validation.get("output_warnings", []),
                "dangerous_operations": validation.get("dangerous_operations", []),
                "business_rules": validation.get("business_rules", []),
                "placeholder_content": validation.get("placeholder_content", []),
                "approval_required": validation.get("approval_required", False),
                "blocked": validation.get("blocked", False),
                "can_execute": validation.get("can_execute", True),
                "dynamic_rules": validation.get("dynamic_rules", []),
            }
            
            session_ctx = {"session_id": session_id, "task": task, "matched_skill_ids": [s["id"] for s in skills_out]} if session_id else None
            return ok({
                "task": task,
                "skills": skills_out,
                "rules": [{"id": r["id"], "name": r["name"], "content": r["content"]} for r in result.get("rules", [])],
                "intent": result.get("intent_analysis", {}),
                "instructions": [s.get("instruction") for s in skills_out if s.get("instruction")],
                "project_instructions": list(set(s.get("project_instruction") for s in skills_out if s.get("project_instruction"))),
                "validation": enhanced_validation,
                "session_context": session_ctx,
            }, trace_id=tid)

    @mcp_server.tool()
    async def skill_list(
        tags: list = None,
        status: str = None, query: str = "", limit: int = 50, offset: int = 0,
        api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            items, total = await skill_service.list_skills(
                session, user_id,
                tags, status, query, limit, offset,
            )
            return ok({"items": [
                {"id": str(s.id), "name": s.name, "tags": s.tags,
                 "version": s.version, "review_status": s.review_status}
                for s in items
            ], "total": total, "limit": limit, "offset": offset}, trace_id=tid)

    @mcp_server.tool()
    async def skill_review(id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            try:
                result = await review_service.run_review(session, UUID(id))
                return ok(result, trace_id=tid)
            except ValueError as e:
                return fail("NOT_FOUND", str(e), tid)

    @mcp_server.tool()
    async def skill_approve(id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import Skill
            skill = await session.get(Skill, UUID(id))
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {id}", tid)
            skill.review_status = "approved"
            await session.commit()
            return ok({"id": id, "status": "approved"}, trace_id=tid)

    @mcp_server.tool()
    async def skill_reject(id: str, reason: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import Skill
            skill = await session.get(Skill, UUID(id))
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {id}", tid)
            skill.review_status = "rejected"
            skill.review_report = reason
            await session.commit()
            return ok({"id": id, "status": "rejected"}, trace_id=tid)

    @mcp_server.tool()
    async def skill_pre_review(content: str, allow_risk_patterns: list = None, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            result = await pre_review_svc(session, content, allow_risk_patterns)
            return ok(result, trace_id=tid)

    @mcp_server.tool()
    async def skill_batch_ops(
        operations: list,
        api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        results = []
        async with async_session_factory() as session:
            for op in operations:
                action = op.get("action")
                try:
                    if action == "register":
                        s = await skill_service.create_skill(session, user_id, op["name"], op["content"])
                        results.append({"success": True, "id": str(s.id)})
                    elif action == "delete":
                        ok_ = await skill_service.delete_skill(session, UUID(op["id"]))
                        results.append({"success": ok_, "id": op.get("id")})
                    elif action == "submit_review":
                        r = await review_service.run_review(session, UUID(op["id"]))
                        results.append({"success": True, "id": op["id"], "status": r["review_status"]})
                    else:
                        results.append({"success": False, "id": op.get("id", ""), "msg": f"unknown action: {action}"})
                except Exception as e:
                    results.append({"success": False, "id": op.get("id", ""), "msg": str(e)})
        failed = sum(1 for r in results if not r["success"])
        return ok({"results": results, "failed_count": failed}, trace_id=tid)

    @mcp_server.tool()
    async def skill_batch_review(ids: list, action: str, reason: str = "", api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        approved, rejected = 0, 0
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import Skill
            for sid in ids:
                skill = await session.get(Skill, UUID(sid))
                if skill:
                    if action == "approve":
                        skill.review_status = "approved"
                        approved += 1
                    elif action == "reject":
                        skill.review_status = "rejected"
                        skill.review_report = reason
                        rejected += 1
            await session.commit()
        return ok({"approved": approved, "rejected": rejected}, trace_id=tid)

    @mcp_server.tool()
    async def rule_create(
        name: str, content: str, tags: list = None,
        priority: int = 0,
        group_name: str = None,
        auto_classify: bool = True,
        api_key: str = None,
    ) -> dict:
        """
        创建新规则
        
        Args:
            name: 规则名称
            content: 规则内容
            tags: 标签列表（可选，自动分类时会自动生成）
            priority: 规则优先级（默认0）
            group_name: 分组名称（可选，自动分类时会自动创建）
            auto_classify: 是否启用自动分类（默认True）
            api_key: API密钥
        """
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        
        async with async_session_factory() as session:
            # 自动分类逻辑
            auto_tags = tags
            auto_group_id = None
            
            if auto_classify and not tags:
                classification = await classification_service.classify_rule(
                    session, name, content,
                    existing_tags=tags,
                )
                auto_tags = classification.get("tags", tags or [])
                suggested_group = classification.get("suggested_group")
                
                # 如果没有指定分组，使用建议的分组
                if not group_name and suggested_group:
                    group_name = suggested_group
            
            # 自动创建分组
            if group_name:
                auto_group_id = await _auto_create_rule_group(session, user_id, group_name)
            
            r = await rule_service.create_rule(
                session, user_id, name, content, auto_tags, priority,
            )
            
            # 更新分组
            if auto_group_id:
                from app.tools.skill_router.db.models import Rule
                rule = await session.get(Rule, r.id)
                rule.group_id = auto_group_id
                await session.commit()
            
            return ok({
                "id": str(r.id),
                "tags": auto_tags,
                "group_id": str(auto_group_id) if auto_group_id else None,
                "group_name": group_name,
            }, trace_id=tid)

    @mcp_server.tool()
    async def rule_update(id: str, api_key: str = None, name: str = None, content: str = None, tags: str = None, priority: int = None, is_active: bool = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        async with async_session_factory() as session:
            r = await rule_service.update_rule(session, UUID(id), name=name, content=content, tags=tag_list, priority=priority, is_active=is_active)
            if not r:
                return fail("NOT_FOUND", f"rule not found: {id}", tid)
            return ok({"id": str(r.id)}, trace_id=tid)

    @mcp_server.tool()
    async def rule_delete(id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            ok_ = await rule_service.delete_rule(session, UUID(id))
            return ok(msg="deleted") if ok_ else fail("NOT_FOUND", f"rule not found: {id}", tid)

    @mcp_server.tool()
    async def rule_list(
        tags: list = None, query: str = "",
        limit: int = 50, offset: int = 0, api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            items, total = await rule_service.list_rules(
                session, user_id,
                tags, query, limit, offset,
            )
            return ok({"items": [{"id": str(r.id), "name": r.name, "tags": r.tags, "priority": r.priority} for r in items], "total": total, "limit": limit, "offset": offset}, trace_id=tid)

    @mcp_server.tool()
    async def evolution_submit(
        target_id: str, target_type: str, new_content: str,
        trigger_reason: str, api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            try:
                evo = await evolution_service.submit_evolution(
                    session, user_id, UUID(target_id), target_type,
                    new_content, trigger_reason,
                )
                return ok({
                    "evolution_id": str(evo.id),
                    "old_version": evo.old_version,
                    "new_version": evo.old_version + 1,
                    "diff_summary": evo.diff_summary or "",
                    "status": evo.status,
                }, trace_id=tid)
            except ValueError as e:
                return fail("NOT_FOUND", str(e), tid)

    @mcp_server.tool()
    async def evolution_rollback(evolution_id: str, trigger_reason: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            try:
                evo = await evolution_service.rollback_evolution(
                    session, UUID(evolution_id), trigger_reason
                )
                return ok({"evolution_id": str(evo.id), "status": evo.status}, trace_id=tid)
            except ValueError as e:
                return fail("NOT_FOUND", str(e), tid)

    @mcp_server.tool()
    async def evolution_list(
        target_id: str = None, target_type: str = None,
        status: str = None, limit: int = 20, offset: int = 0,
        api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            items, total = await evolution_service.list_evolutions(
                session, user_id,
                UUID(target_id) if target_id else None,
                target_type, status, None, limit, offset,
            )
            return ok({"items": [
                {"evolution_id": str(e.id), "target_name": e.target_name,
                 "diff_summary": e.diff_summary or "", "status": e.status,
                 "created_at": str(e.created_at)}
                for e in items
            ], "total": total, "limit": limit, "offset": offset}, trace_id=tid)

    @mcp_server.tool()
    async def cache_flush(key_hash: str = None, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        await delete_cache(key_hash=key_hash)
        return ok(msg="flushed", trace_id=tid)

    @mcp_server.tool()
    async def cache_flush_by_target(resource_type: str, resource_id: str, api_key: str = None) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        await delete_cache(pattern=f"*{resource_id}*")
        return ok(msg="flushed by target", trace_id=tid)

    @mcp_server.tool()
    async def tag_global_manage(
        action: str, old_tag: str, new_tag: str = None, api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        return ok({"action": action, "old_tag": old_tag, "new_tag": new_tag}, trace_id=tid)

    @mcp_server.tool()
    async def embedding_model_detect(
        endpoint: str = None, api_key: str = None, model: str = None, mcp_api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(mcp_api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid mcp_api_key", tid)
        dim = await detect_embedding_dim(
            endpoint or settings.embedding_endpoint,
            api_key or settings.embedding_api_key,
            model or settings.embedding_model,
        )
        if dim is None:
            return fail("LLM_TIMEOUT", "failed to detect embedding dimension", tid)
        return ok({"dim": dim}, trace_id=tid)

    @mcp_server.tool()
    async def review_pattern_manage(
        action: str, id: str = None, name: str = None,
        pattern: str = None, risk_level: str = "high", api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import ReviewPattern
            if action == "list":
                result = await session.execute(select(ReviewPattern).where(ReviewPattern.user_id == user_id))
                patterns = result.scalars().all()
                return ok({"items": [{"id": str(p.id), "name": p.name, "pattern": p.pattern, "risk_level": p.risk_level} for p in patterns]}, trace_id=tid)
            elif action == "create":
                rp = ReviewPattern(name=name, pattern=pattern, risk_level=risk_level, user_id=user_id)
                session.add(rp)
                await session.commit()
                return ok({"id": str(rp.id)}, trace_id=tid)
            elif action == "delete" and id:
                rp = await session.get(ReviewPattern, UUID(id))
                if rp:
                    await session.delete(rp)
                    await session.commit()
                return ok(msg="deleted", trace_id=tid)
        return fail("INVALID_PARAM", f"unknown action: {action}", tid)

    @mcp_server.tool()
    async def model_add(
        name: str, endpoint: str, api_key: str, model_name: str,
        role: str, is_default: bool = False, temperature: float = 0.7,
        max_tokens: int = 2048, timeout_secs: int = 30, mcp_api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(mcp_api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid mcp_api_key", tid)
        async with async_session_factory() as session:
            cfg = await model_service.add_model(
                session, user_id, name, endpoint, api_key, model_name,
                role, is_default, temperature, max_tokens, timeout_secs,
            )
            return ok({"id": str(cfg.id)}, trace_id=tid)

    @mcp_server.tool()
    async def model_list(role: str = None, mcp_api_key: str = None) -> dict:
        user_id = await _get_user_id(mcp_api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid mcp_api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import LLMConfig
            stmt = select(LLMConfig).where(LLMConfig.user_id == user_id)
            if role:
                stmt = stmt.where(LLMConfig.role == role)
            result = await session.execute(stmt)
            cfgs = result.scalars().all()
            return ok({"items": [
                {"id": str(c.id), "name": c.name, "model_name": c.model_name,
                 "role": c.role, "is_healthy": c.is_healthy, "is_default": c.is_default}
                for c in cfgs
            ]}, trace_id=tid)

    @mcp_server.tool()
    async def stats_get(metric: str = None, range_hours: int = 24, api_key: str = None) -> dict:
        """Get comprehensive system statistics and monitoring data."""
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from sqlalchemy import func, select, text
            from app.tools.skill_router.db.models import OperationLog, Skill, Rule
            from datetime import datetime, timedelta
            
            # 时间范围计算（使用naive datetime以匹配数据库）
            now = datetime.utcnow()
            start_time = now - timedelta(hours=range_hours)
            
            # P4增强：完整的实时监控数据
            
            # 1. Resolve统计
            resolve_count_result = await session.execute(
                select(func.count()).select_from(OperationLog)
                .where(OperationLog.action == "resolve")
                .where(OperationLog.created_at >= start_time)
            )
            resolve_count = resolve_count_result.scalar() or 0
            
            # 2. Cache命中率统计（从cache_service获取）
            from app.tools.skill_router.services.cache_service import get_cache_statistics
            cache_stats = await get_cache_statistics()
            
            # 3. 模式分布统计（简化版，使用原始SQL）
            mode_distribution = {}
            # TODO: 需要从detail字段提取mode，但目前简化处理
            
            # 4. LLM失败率统计
            llm_fail_result = await session.execute(
                select(func.count()).select_from(OperationLog)
                .where(OperationLog.action == "llm_fail")
                .where(OperationLog.created_at >= start_time)
            )
            llm_fail_count = llm_fail_result.scalar() or 0
            llm_fail_rate = llm_fail_count / resolve_count if resolve_count > 0 else 0
            
            # 5. Embedding失败率统计
            embedding_fail_result = await session.execute(
                select(func.count()).select_from(OperationLog)
                .where(OperationLog.action == "embedding_fail")
                .where(OperationLog.created_at >= start_time)
            )
            embedding_fail_count = embedding_fail_result.scalar() or 0
            embedding_fail_rate = embedding_fail_count / resolve_count if resolve_count > 0 else 0
            
            # 6. 平均延迟统计（需要记录在OperationLog中）
            avg_latency = 0
            
            # 7. Top技能使用统计
            top_skills_result = await session.execute(
                select(Skill.name, func.count().label("count"))
                .join(OperationLog, Skill.id == OperationLog.resource_id)
                .where(OperationLog.resource_type == "skill")
                .where(OperationLog.action == "resolve")
                .where(OperationLog.created_at >= start_time)
                .group_by(Skill.name)
                .order_by(func.count().desc())
                .limit(10)
            )
            top_skills = top_skills_result.all() or []
            
            # 8. Top规则使用统计
            top_rules_result = await session.execute(
                select(Rule.name, func.count().label("count"))
                .join(OperationLog, Rule.id == OperationLog.resource_id)
                .where(OperationLog.resource_type == "rule")
                .where(OperationLog.action == "resolve")
                .where(OperationLog.created_at >= start_time)
                .group_by(Rule.name)
                .order_by(func.count().desc())
                .limit(10)
            )
            top_rules = top_rules_result.all() or []
            
            # 9. 系统负载统计（从rate_limiter获取）
            from app.tools.skill_router.services.rate_limiter import check_system_load
            system_load = await check_system_load()
            
            # 10. 用户活跃度统计
            active_users_result = await session.execute(
                select(func.count(func.distinct(OperationLog.user_id)))
                .where(OperationLog.created_at >= start_time)
            )
            active_users = active_users_result.scalar() or 0
            
            # 11. 技能库统计
            total_skills_result = await session.execute(
                select(func.count()).select_from(Skill)
            )
            total_skills = total_skills_result.scalar() or 0
            approved_skills_result = await session.execute(
                select(func.count()).select_from(Skill)
                .where(Skill.review_status == "approved")
            )
            approved_skills = approved_skills_result.scalar() or 0
            
            # 12. 规则库统计
            total_rules_result = await session.execute(
                select(func.count()).select_from(Rule)
            )
            total_rules = total_rules_result.scalar() or 0
            
            return ok({
                "resolve_count": resolve_count,
                "cache_hit_rate": cache_stats.get("hit_rate", 0),
                "session_hit_rate": cache_stats.get("session_hit_rate", 0),
                "cache_stats": cache_stats,
                "mode_distribution": mode_distribution,
                "llm_fail_rate": round(llm_fail_rate, 4),
                "embedding_fail_rate": round(embedding_fail_rate, 4),
                "avg_latency_ms": avg_latency,
                "top_skills": [{"name": s, "count": c} for s, c in top_skills],
                "top_rules": [{"name": r, "count": c} for r, c in top_rules],
                "system_load": system_load,
                "active_users": active_users,
                "total_skills": total_skills,
                "approved_skills": approved_skills,
                "total_rules": total_rules,
                "time_range": {
                    "start": str(start_time),
                    "end": str(now),
                    "hours": range_hours,
                },
            }, trace_id=tid)

    @mcp_server.tool()
    async def operation_log_list(
        resource_type: str = None, resource_id: str = None,
        action: str = None, limit: int = 50, offset: int = 0,
        api_key: str = None,
    ) -> dict:
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import OperationLog
            stmt = select(OperationLog).where(OperationLog.user_id == user_id)
            if resource_type:
                stmt = stmt.where(OperationLog.resource_type == resource_type)
            if resource_id:
                stmt = stmt.where(OperationLog.resource_id == UUID(resource_id))
            if action:
                stmt = stmt.where(OperationLog.action == action)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = await session.scalar(count_stmt)
            stmt = stmt.order_by(OperationLog.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            logs = result.scalars().all()
            return ok({
                "items": [
                    {"id": str(l.id), "resource_type": l.resource_type, "action": l.action,
                     "detail": l.detail, "trace_id": l.trace_id, "created_at": str(l.created_at)}
                    for l in logs
                ],
                "total": total or 0,
                "limit": limit,
                "offset": offset,
            }, trace_id=tid)

    @mcp_server.tool()
    async def validate_skill_params(skill_id: str, params: dict, api_key: str = None, user_role: str = None) -> dict:
        """Validate parameters against a skill's parameter schema before execution."""
        user_id = await _get_user_id(api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid api_key", tid)
        async with async_session_factory() as session:
            from app.tools.skill_router.db.models import Skill
            skill = await session.get(Skill, UUID(skill_id))
            if not skill:
                return fail("NOT_FOUND", f"skill not found: {skill_id}", tid)
            
            # P0: 使用增强的校验逻辑
            from app.tools.skill_router.services.validation_service import validate_skill_execution
            skill_data = {
                "id": str(skill.id),
                "name": skill.name,
                "exec_config": skill.exec_config or {},
                "sensitive": skill.sensitive,
                "review_status": skill.review_status,
                "allowed_roles": skill.allowed_roles,
            }
            validation_result = validate_skill_execution(skill_data, params, user_role)
            
            return ok({
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"],
                "approval_required": validation_result["approval_required"],
                "dynamic_rules": validation_result["dynamic_rules"],
            }, trace_id=tid)

    @mcp_server.tool()
    async def resource_export(resource_type: str, resource_id: str, format: str = "markdown", mcp_api_key: str = None) -> dict:
        user_id = await _get_user_id(mcp_api_key)
        if not user_id:
            return fail("PERMISSION_DENIED", "invalid mcp_api_key", tid)
        async with async_session_factory() as session:
            if resource_type == "skill":
                from app.tools.skill_router.db.models import Skill
                obj = await session.get(Skill, UUID(resource_id))
            elif resource_type == "rule":
                from app.tools.skill_router.db.models import Rule
                obj = await session.get(Rule, UUID(resource_id))
            else:
                return fail("INVALID_PARAM", f"unknown resource_type: {resource_type}", tid)
            if not obj:
                return fail("NOT_FOUND", f"{resource_type} not found: {resource_id}", tid)
            content = f"# {obj.name}\n\n{obj.content}"
            return ok({"content": content, "metadata": {
                "name": obj.name, "type": resource_type, "id": resource_id,
                "version": getattr(obj, "version", 1),
            }}, trace_id=tid)
