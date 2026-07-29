import re
from typing import Optional
from sqlalchemy import select
from app.tools.quality_tool.db.models import CheckResult, async_session
from app.tools.quality_tool.config import settings


def lint_code(code: str, filename: Optional[str] = None) -> list:
    issues = []
    lines = code.split("\n")

    for i, line in enumerate(lines, 1):
        if len(line) > settings.LINT_MAX_LINE_LENGTH:
            issues.append({
                "line": i,
                "rule": "line-length",
                "message": f"Line too long ({len(line)} > {settings.LINT_MAX_LINE_LENGTH})",
                "severity": "warning",
            })
        if settings.LINT_CHECK_TRAILING_WHITESPACE and line != line.rstrip():
            issues.append({
                "line": i,
                "rule": "trailing-whitespace",
                "message": "Trailing whitespace",
                "severity": "warning",
            })

    if settings.LINT_CHECK_MISSING_NEWLINE and code and not code.endswith("\n"):
        issues.append({
            "line": len(lines),
            "rule": "missing-newline",
            "message": "File does not end with newline",
            "severity": "info",
        })

    return issues


def security_scan(code: str, filename: Optional[str] = None) -> list:
    issues = []

    secret_patterns = [
        (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"(?:api_key|apikey|api-key)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (r"(?:secret|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret/token"),
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private key found"),
    ]

    if settings.SECURITY_CHECK_HARDCODED_SECRETS:
        for pattern, desc in secret_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + 1
                issues.append({
                    "line": line_num,
                    "rule": "hardcoded-secret",
                    "message": desc,
                    "severity": "critical",
                })

    sql_injection_patterns = [
        (r"""(?:execute|cursor\.execute)\s*\(\s*['\"].*%s""", "SQL string formatting (possible injection)"),
        (r"""(?:execute|cursor\.execute)\s*\(\s*f['\"]""", "SQL f-string (possible injection)"),
        (r"""(?:execute|cursor\.execute)\s*\(\s*['\"].*\+""", "SQL concatenation (possible injection)"),
    ]

    if settings.SECURITY_CHECK_SQL_INJECTION:
        for pattern, desc in sql_injection_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + 1
                issues.append({
                    "line": line_num,
                    "rule": "sql-injection",
                    "message": desc,
                    "severity": "high",
                })

    dangerous_patterns = [
        (r"\beval\s*\(", "Use of eval()"),
        (r"\bexec\s*\(", "Use of exec()"),
        (r"\bos\.system\s*\(", "Use of os.system()"),
        (r"\bsubprocess\.call\s*\(\s*['\"]", "Subprocess with shell=True risk"),
        (r"\bpickle\.loads?\s*\(", "Pickle deserialization"),
    ]

    if settings.SECURITY_CHECK_DANGEROUS_FUNCTIONS:
        for pattern, desc in dangerous_patterns:
            for match in re.finditer(pattern, code):
                line_num = code[:match.start()].count("\n") + 1
                issues.append({
                    "line": line_num,
                    "rule": "dangerous-function",
                    "message": desc,
                    "severity": "medium",
                })

    return issues


async def run_check(
    code: str,
    check_type: str,
    filename: Optional[str] = None,
    language: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    if check_type == "lint":
        issues = lint_code(code, filename)
    elif check_type == "security":
        issues = security_scan(code, filename)
    elif check_type == "all":
        issues = lint_code(code, filename) + security_scan(code, filename)
    else:
        return {"error": f"Unknown check_type: {check_type}. Use: lint, security, all"}

    async with async_session() as session:
        record = CheckResult(
            user_id=user_id,
            filename=filename,
            language=language,
            check_type=check_type,
            issues=issues,
            issue_count=len(issues),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    return {
        "id": record.id,
        "checkType": check_type,
        "issues": issues,
        "issueCount": len(issues),
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


async def get_history(user_id: Optional[int] = None, limit: int = 20) -> list:
    async with async_session() as session:
        q = select(CheckResult)
        if user_id:
            q = q.where(CheckResult.user_id == user_id)
        q = q.order_by(CheckResult.id.desc()).limit(limit)
        result = await session.execute(q)
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "checkType": r.check_type,
                "issueCount": r.issue_count,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
