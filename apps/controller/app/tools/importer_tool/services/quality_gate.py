from typing import Optional

import httpx

from app.tools.importer_tool.config import settings


class QualityResult:
    def __init__(self, passed: bool, issues: list[dict], summary: dict,
                 source: str = "controller"):
        self.passed = passed
        self.issues = issues
        self.summary = summary
        self.source = source

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "summary": self.summary,
            "source": self.source,
        }


async def run_quality_check(content: str, filename: Optional[str] = None,
                            content_type: Optional[str] = None) -> QualityResult:
    issues: list[dict] = []
    controller_available = False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.CONTROLLER_URL}/api/quality/check",
                json={"code": content, "filename": filename or "imported.md"},
            )
            if resp.status_code == 200:
                controller_available = True
                data = resp.json()
                issues = data.get("issues", [])
    except Exception:
        pass

    extra_issues = _extra_checks(content, content_type)
    issues.extend(extra_issues)

    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    error_count = sum(1 for i in issues if i.get("severity") == "error")
    warning_count = sum(1 for i in issues if i.get("severity") == "warning")
    info_count = sum(1 for i in issues if i.get("severity") == "info")

    passed = critical_count == 0 and error_count == 0

    return QualityResult(
        passed=passed,
        issues=issues,
        summary={
            "total": len(issues),
            "critical": critical_count,
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
        },
        source="controller" if controller_available else "builtin",
    )


_BUILTIN_ISSUES = []


def _extra_checks(content: str, content_type: Optional[str] = None) -> list[dict]:
    issues: list[dict] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append({
                "line": i, "rule": "line-length",
                "message": f"Line too long ({len(line)} > 120)",
                "severity": "warning",
            })
        if line != line.rstrip():
            issues.append({
                "line": i, "rule": "trailing-whitespace",
                "message": "Trailing whitespace",
                "severity": "warning",
            })

    if content and not content.endswith("\n"):
        issues.append({
            "line": len(lines), "rule": "missing-newline",
            "message": "File does not end with newline",
            "severity": "info",
        })

    _security_patterns = [
        (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password", "critical"),
        (r"(?:api_key|apikey|api-key)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key", "critical"),
        (r"(?:secret|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret/token", "critical"),
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private key detected", "critical"),
        (r"\beval\s*\(", "Use of eval()", "medium"),
        (r"\bexec\s*\(", "Use of exec()", "medium"),
    ]

    import re
    for pattern, msg, severity in _security_patterns:
        for m in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:m.start()].count("\n") + 1
            issues.append({
                "line": line_num, "rule": "security",
                "message": msg, "severity": severity,
            })

    if content_type == "rule":
        has_severity = bool(__import__("re").search(r"(?m)^severity\s*[=:]", content))
        if not has_severity:
            issues.append({
                "line": 1, "rule": "rule-missing-severity",
                "message": "Rule content must include a 'severity' field",
                "severity": "error",
            })

    if content_type == "skill":
        has_instruction = bool(__import__("re").search(r"(?m)^instruction\s*[=:]", content))
        has_content_field = bool(__import__("re").search(r"(?m)^content\s*[=:]", content))
        if not has_instruction and not has_content_field:
            issues.append({
                "line": 1, "rule": "skill-missing-content",
                "message": "Skill content should include 'instruction' or 'content' section",
                "severity": "error",
            })

    issues.sort(key=lambda x: {"critical": 0, "error": 1, "warning": 2, "info": 3}.get(x["severity"], 99))
    return issues
