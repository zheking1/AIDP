import re
from typing import Optional


CLASSIFICATION_RESULT = tuple[
    str,   # type: knowledge / skill / rule / plan
    str,   # confidence: high / medium / low
    str,   # title
]


def classify_content(content: str, filename: Optional[str] = None) -> dict:
    ctype, confidence, title = _classify(content, filename)
    return {
        "type": ctype,
        "confidence": confidence,
        "title": title,
    }


def _extract_title(content: str, filename: Optional[str] = None) -> str:
    if not content:
        return filename or "untitled"

    for line in content.split("\n")[:20]:
        line = line.strip()
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return m.group(1).strip()

    if filename:
        name = filename.rsplit(".", 1)[0]
        name = re.sub(r"[-_]", " ", name)
        return name.title()

    return "untitled"


def _classify(content: str, filename: Optional[str] = None) -> CLASSIFICATION_RESULT:
    if not content:
        return ("knowledge", "low", filename or "untitled")

    name_lower = (filename or "").lower()
    content_lower = content.lower()
    title = _extract_title(content, filename)

    has_instruction = bool(re.search(r"(?m)^instruction\s*[=:]", content))
    has_content_field = bool(re.search(r"(?m)^content\s*[=:]", content))
    has_severity = bool(re.search(r"(?m)^severity\s*[=:]\s*(critical|high|medium|low)", content))
    has_constraint = bool(re.search(r"(必须|禁止|不得|应当|不允许|约束)", content))

    if has_instruction and has_content_field:
        return ("skill", "high", title)

    if has_severity and has_constraint:
        return ("rule", "high", title)

    if "adr" in name_lower:
        return ("knowledge", "high", title)

    if "plan" in name_lower or "蓝图" in name_lower or "方案" in name_lower or "路线图" in name_lower:
        return ("plan", "medium", title)

    if "readme" in name_lower or "架构" in name_lower or "设计" in name_lower:
        return ("knowledge", "medium", title)

    if name_lower.endswith(".md") and content.startswith("#"):
        return ("knowledge", "medium", title)

    if has_severity:
        return ("rule", "medium", title)

    return ("knowledge", "low", title)
