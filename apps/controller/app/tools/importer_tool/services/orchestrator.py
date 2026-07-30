import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.tools.importer_tool.db.models import async_session, ImportSession, ImportItem
from app.tools.importer_tool.services.acquirer import (
    acquire_text, acquire_url, acquire_file,
    scan_directory, acquire_directory_file,
)
from app.tools.importer_tool.services.classifier import classify_content, _extract_title
from app.tools.importer_tool.services.categorizer import recommend_tags
from app.tools.importer_tool.services.quality_gate import run_quality_check
from app.tools.importer_tool.services.persister import persist_by_type


def _new_id() -> str:
    return uuid.uuid4().hex[:24]


async def handle_import(params: dict, trace_id: str = "", context: dict = None) -> dict:
    source = params.get("source", {})
    source_type = source.get("type", "text")
    session_id = params.get("session_id")
    confirm = params.get("confirm")
    auto_confirm = params.get("auto_confirm", False)
    scope = params.get("scope", "personal")
    project_id = params.get("project_id")
    user_id = (context or {}).get("user_id", "system")

    if session_id and confirm:
        return await _confirm_import(session_id, confirm, user_id)

    acquired = None
    filename = None
    source_uri = None

    if source_type == "text":
        acquired = await acquire_text(source.get("content", ""), source.get("name"))
    elif source_type == "url":
        acquired = await acquire_url(source.get("url", ""), source.get("name"))
        source_uri = source.get("url")
    elif source_type == "file":
        acquired = await acquire_file(source.get("path", ""))
        source_uri = source.get("path")
    else:
        return {"error": f"Unsupported source type: {source_type}"}

    content = acquired.content
    filename = acquired.filename
    source_uri = source_uri or acquired.source_uri

    classification = classify_content(content, filename)
    ctype = classification["type"]
    title = classification["title"]
    if not content.strip():
        title = source.get("name") or filename or "untitled"

    categorization = recommend_tags(content, filename, ctype)
    tags = categorization["tags"]
    category = categorization["category"]
    severity = categorization["severity"]

    quality = await run_quality_check(content, filename, ctype)

    if auto_confirm:
        persist_result = await persist_by_type(
            content_type=ctype, title=title, content=content,
            tags=tags, category=category, severity=severity,
            scope=scope, user_id=user_id,
        )
        return _build_completed_response(session_id or _new_id(), classification, quality, persist_result)

    session_id = _new_id()
    async with async_session() as db:
        session = ImportSession(
            id=session_id,
            user_id=user_id,
            project_id=project_id,
            scope=scope,
            source_type=source_type,
            source_uri=source_uri,
            status="awaiting_confirmation",
            total_items=1,
        )
        db.add(session)

        item = ImportItem(
            id=_new_id(),
            session_id=session_id,
            item_index=0,
            filename=filename,
            content=content,
            content_hash=acquired.checksum,
            classified_type=ctype,
            classified_confidence=classification.get("confidence", "low"),
            suggested_title=title,
            suggested_tags=str(tags),
            suggested_category=category,
            suggested_severity=severity,
            quality_passed=int(quality.passed) if quality.passed else 0,
            quality_issues=str(quality.issues),
            status="awaiting_confirmation",
        )
        db.add(item)
        await db.commit()

    return {
        "session_id": session_id,
        "status": "awaiting_confirmation",
        "classification": {
            "type": ctype,
            "confidence": classification.get("confidence", "low"),
            "title": title,
            "suggested_tags": tags,
            "suggested_category": category,
            "suggested_severity": severity,
        },
        "quality_check": quality.to_dict(),
        "content_preview": content[:500] if len(content) > 500 else content,
    }


async def handle_import_batch(params: dict, trace_id: str = "", context: dict = None) -> dict:
    source = params.get("source", {})
    source_type = source.get("type")
    path = source.get("path", "")
    confirm = params.get("confirm")
    scope = params.get("scope", "personal")
    project_id = params.get("project_id")
    user_id = (context or {}).get("user_id", "system")

    if confirm:
        return await _confirm_batch_import(confirm, user_id, scope, project_id)

    if source_type != "directory":
        return {"error": "import_batch only supports directory source type"}

    entries = await scan_directory(path, source.get("pattern"))
    if not entries:
        return {"status": "completed", "items": [], "summary": {"total": 0}}

    session_id = _new_id()
    items_data = []

    async with async_session() as db:
        session = ImportSession(
            id=session_id,
            user_id=user_id,
            project_id=project_id,
            scope=scope,
            source_type="directory",
            source_uri=path,
            status="awaiting_confirmation",
            total_items=len(entries),
        )
        db.add(session)

        for idx, entry in enumerate(entries):
            acquired = await acquire_directory_file(path, entry.path)
            classification = classify_content(acquired.content, entry.filename)
            categorization = recommend_tags(acquired.content, entry.filename, classification["type"])
            quality = await run_quality_check(acquired.content, entry.filename, classification["type"])

            item = ImportItem(
                id=_new_id(),
                session_id=session_id,
                item_index=idx,
                filename=entry.filename,
                content=acquired.content,
                content_hash=acquired.checksum,
                classified_type=classification["type"],
                classified_confidence=classification.get("confidence", "low"),
                suggested_title=classification.get("title", entry.filename),
                suggested_tags=str(categorization["tags"]),
                suggested_category=categorization["category"],
                suggested_severity=categorization["severity"],
                quality_passed=int(quality.passed) if quality.passed else 0,
                quality_issues=str(quality.issues),
                status="awaiting_confirmation",
            )
            db.add(item)

            items_data.append({
                "path": entry.path,
                "filename": entry.filename,
                "classification": classification,
                "categorization": categorization,
                "quality": quality.to_dict(),
            })

        await db.commit()

    summary = _build_batch_summary(items_data)
    return {
        "session_id": session_id,
        "status": "awaiting_confirmation",
        "items": items_data,
        "summary": summary,
    }


async def _confirm_import(session_id: str, confirm: dict, user_id: str) -> dict:
    ctype = confirm.get("type")
    tags = confirm.get("tags", [])
    category = confirm.get("category", "")
    severity = confirm.get("severity")
    skip_warnings = confirm.get("skip_quality_warnings", False)

    async with async_session() as db:
        result = await db.execute(
            select(ImportSession).where(ImportSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"error": "Session not found", "session_id": session_id}

        item_result = await db.execute(
            select(ImportItem).where(
                ImportItem.session_id == session_id,
                ImportItem.item_index == 0,
            )
        )
        item = item_result.scalar_one_or_none()
        if not item:
            return {"error": "Item not found in session", "session_id": session_id}

        if not skip_warnings and item.quality_passed == 0:
            return {
                "session_id": session_id,
                "status": "blocked",
                "error": "Quality check failed. Set skip_quality_warnings=true to override.",
            }

        item.confirmed_type = ctype or item.classified_type
        item.confirmed_tags = str(tags)
        item.confirmed_category = category or item.suggested_category
        item.confirmed_severity = severity or item.suggested_severity
        item.status = "persisting"
        await db.flush()

    tags_final = tags or (
        json.loads(item.suggested_tags) if isinstance(item.suggested_tags, str)
        else item.suggested_tags or []
    )
    category_final = category or item.suggested_category or ""
    severity_final = severity or item.suggested_severity

    persist_result = await persist_by_type(
        content_type=item.confirmed_type or item.classified_type or "knowledge",
        title=item.suggested_title or item.filename or "untitled",
        content=item.content or "",
        tags=tags_final,
        category=category_final,
        severity=severity_final,
        user_id=user_id,
    )

    async with async_session() as db:
        s_result = await db.execute(
            select(ImportSession).where(ImportSession.id == session_id)
        )
        session = s_result.scalar_one_or_none()
        item_result = await db.execute(
            select(ImportItem).where(ImportItem.id == item.id)
        )
        item = item_result.scalar_one_or_none()

        if persist_result.success:
            item.status = "persisted"
            item.persist_type = persist_result.target_type
            item.persist_id = persist_result.target_id
            item.persist_url = persist_result.target_url
            item.persist_version = persist_result.version
            item.persisted_at = datetime.now(timezone.utc)

            session.status = "completed"
            session.completed_items += 1
            session.completed_at = datetime.now(timezone.utc)
        else:
            item.status = "failed"
            item.error_message = persist_result.error
            session.status = "failed"
            session.failed_items += 1

        await db.commit()

    return _build_completed_response(session_id, {}, None, persist_result)


async def _confirm_batch_import(confirm: list[dict], user_id: str,
                                scope: str, project_id: Optional[int]) -> dict:
    if not confirm:
        return {"status": "failed", "error": "Empty confirm list"}

    session_id = confirm[0].get("session_id")
    if not session_id:
        return {"status": "failed", "error": "Missing session_id in confirm"}

    async with async_session() as db:
        result = await db.execute(
            select(ImportSession).where(ImportSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"error": "Session not found", "session_id": session_id}

        total = session.total_items
        completed = 0
        failed = 0
        skipped = 0
        results_list = []

        for conf in confirm:
            item_index = conf.get("item_index")
            if item_index is None:
                continue

            item_result = await db.execute(
                select(ImportItem).where(
                    ImportItem.session_id == session_id,
                    ImportItem.item_index == item_index,
                )
            )
            item = item_result.scalar_one_or_none()
            if not item:
                skipped += 1
                continue

            ctype = conf.get("type") or item.classified_type
            tags = conf.get("tags", json.loads(item.suggested_tags) if item.suggested_tags else [])
            category = conf.get("category", item.suggested_category or "")
            severity = conf.get("severity", item.suggested_severity)
            skip_warnings = conf.get("skip_quality_warnings", False)

            if not skip_warnings and item.quality_passed == 0:
                item.status = "blocked"
                item.error_message = "Quality check failed"
                failed += 1
                await db.flush()
                continue

            item.confirmed_type = ctype
            item.confirmed_tags = str(tags)
            item.confirmed_category = category
            item.confirmed_severity = severity
            item.status = "persisting"
            await db.flush()

            persist_result = await persist_by_type(
                content_type=ctype or "knowledge",
                title=item.suggested_title or item.filename or "untitled",
                content=item.content or "",
                tags=tags,
                category=category,
                severity=severity,
                scope=scope,
                user_id=user_id,
            )

            if persist_result.success:
                item.status = "persisted"
                item.persist_type = persist_result.target_type
                item.persist_id = persist_result.target_id
                item.persist_url = persist_result.target_url
                item.persist_version = persist_result.version
                item.persisted_at = datetime.now(timezone.utc)
                completed += 1
            else:
                item.status = "failed"
                item.error_message = persist_result.error
                failed += 1

            results_list.append({
                "item_index": item_index,
                "filename": item.filename,
                "success": persist_result.success,
                "target_type": persist_result.target_type,
                "target_id": persist_result.target_id,
                "error": persist_result.error,
            })

            await db.flush()

        session.completed_items = completed
        session.failed_items = failed
        session.skipped_items = skipped
        session.status = "completed" if failed == 0 else "partial"
        if session.status == "completed":
            session.completed_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "session_id": session_id,
        "status": session.status,
        "summary": {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
        },
        "results": results_list,
    }


def _build_completed_response(session_id: str, classification, quality, persist_result) -> dict:
    resp = {
        "session_id": session_id,
        "status": "completed" if persist_result and persist_result.success else "failed",
        "summary": "",
    }
    if classification:
        resp["classification"] = classification
    if quality:
        resp["quality_check"] = quality.to_dict() if hasattr(quality, 'to_dict') else quality
    if persist_result:
        resp["result"] = persist_result.to_dict()
        if persist_result.success and not persist_result.skipped:
            resp["summary"] = f"已导入，目标ID: {persist_result.target_id}"
        elif persist_result.skipped:
            resp["summary"] = "内容已存在，跳过导入"
        else:
            resp["summary"] = f"导入失败: {persist_result.error}"
    return resp


def _build_batch_summary(items: list[dict]) -> dict:
    total = len(items)
    types: dict[str, int] = {}
    warnings = 0
    blocked = 0

    for item in items:
        ctype = item.get("classification", {}).get("type", "unknown")
        types[ctype] = types.get(ctype, 0) + 1

        quality = item.get("quality", {})
        summary = quality.get("summary", {})
        if summary.get("warnings", 0) > 0:
            warnings += 1
        if not quality.get("passed", True):
            blocked += 1

    return {
        "total": total,
        "by_type": types,
        "with_warnings": warnings,
        "blocked": blocked,
    }
