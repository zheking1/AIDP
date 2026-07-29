"""
Quality Module Routes
质量检查 API 路由
"""
import json, re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_factory
from app.modules.quality.models import CheckResult
from app.core.permissions import require_permissions
from app.api.auth import get_current_user

router = APIRouter()

LINT_MAX_LINE_LENGTH = 120
LINT_CHECK_TRAILING_WHITESPACE = True
LINT_CHECK_MISSING_NEWLINE = True
SECURITY_CHECK_HARDCODED_SECRETS = True
SECURITY_CHECK_SQL_INJECTION = True
SECURITY_CHECK_DANGEROUS_FUNCTIONS = True


class CheckRequest(BaseModel):
    code: str = Field(..., min_length=1)
    filename: Optional[str] = None
    language: Optional[str] = None


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def lint_code(code: str) -> list:
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        if len(line) > LINT_MAX_LINE_LENGTH:
            issues.append({"line": i, "rule": "line-length", "message": f"行过长 ({len(line)} > {LINT_MAX_LINE_LENGTH})", "severity": "warning"})
        if LINT_CHECK_TRAILING_WHITESPACE and line != line.rstrip():
            issues.append({"line": i, "rule": "trailing-whitespace", "message": "行尾多余空格", "severity": "warning"})
    if LINT_CHECK_MISSING_NEWLINE and code and not code.endswith("\n"):
        issues.append({"line": len(lines), "rule": "missing-newline", "message": "文件末尾缺少换行", "severity": "info"})
    return issues


def security_scan(code: str) -> list:
    issues = []
    patterns = [
        (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", "硬编码密码", "critical"),
        (r"(?:api_key|apikey|api-key)\s*=\s*['\"][^'\"]+['\"]", "硬编码 API 密钥", "critical"),
        (r"(?:secret|token)\s*=\s*['\"][^'\"]+['\"]", "硬编码密钥/令牌", "critical"),
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "发现私钥", "critical"),
        (r"\beval\s*\(", "使用 eval()", "medium"),
        (r"\bexec\s*\(", "使用 exec()", "medium"),
        (r"\bos\.system\s*\(", "使用 os.system()", "medium"),
        (r"\bpickle\.loads?\s*\(", "Pickle 反序列化", "medium"),
    ]
    for pattern, desc, severity in patterns:
        for match in re.finditer(pattern, code, re.IGNORECASE):
            line_num = code[:match.start()].count("\n") + 1
            issues.append({"line": line_num, "rule": "security", "message": desc, "severity": severity})
    return issues


@router.post("/check")
async def run_quality_check(
    data: CheckRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    lint_issues = lint_code(data.code)
    sec_issues = security_scan(data.code)
    all_issues = lint_issues + sec_issues

    record = CheckResult(
        user_id=str(getattr(user, 'id', '') or ''),
        filename=data.filename, language=data.language,
        check_type="all", issues=json.dumps(all_issues, ensure_ascii=False),
        issue_count=len(all_issues),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": record.id, "checkType": "all",
        "issues": all_issues, "issueCount": len(all_issues),
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/history")
async def get_check_history(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CheckResult).order_by(desc(CheckResult.created_at)).limit(limit)
    )
    items = []
    for r in result.scalars().all():
        d = r.to_dict()
        d["issues"] = json.loads(r.issues) if r.issues else []
        items.append(d)
    return items


@router.get("/history/{record_id}")
async def get_check_history_detail(
    record_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CheckResult).where(CheckResult.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    issues = json.loads(record.issues) if record.issues else []
    return {
        "id": record.id, "filename": record.filename, "language": record.language,
        "checkType": record.check_type,
        "issues": issues, "issueCount": record.issue_count,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }