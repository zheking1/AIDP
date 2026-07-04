import re
from typing import Dict, List, Optional


PRIVACY_PATTERNS = {
    "api_key": [
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
    ],
    "secret": [
        r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']+)["\']?',
    ],
    "token": [
        r'(?i)(token|access_token|bearer)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
    ],
    "email": [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ],
    "phone": [
        r'(?:(?:\+|00)[1-7]\s*)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}',
    ],
    "aws_key": [
        r'AKIA[0-9A-Z]{16}',
    ],
}


class PrivacyFilter:
    def filter(self, text: str) -> Dict:
        masked = text
        findings = []

        for category, patterns in PRIVACY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, masked)
                for match in matches:
                    original = match[0] if isinstance(match, tuple) else match
                    findings.append({"type": category, "value": original[:10] + "***"})
                    replacement = f"[REDACTED_{category.upper()}]"
                    masked = masked.replace(original, replacement)

        return {"filtered_text": masked, "findings": findings}


def sanitize(text: str) -> str:
    filter = PrivacyFilter()
    result = filter.filter(text)
    return result["filtered_text"]
