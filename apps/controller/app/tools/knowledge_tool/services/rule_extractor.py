import os
import re
from typing import List, Dict


class CodingRuleExtractor:
    """从代码库提取编码规则"""

    def extract_from_comments(self, project_path: str) -> List[Dict]:
        rules = []
        patterns = [
            (r'# TODO:?\s*(.+)', "todo"),
            (r'# FIXME:?\s*(.+)', "fixme"),
            (r'# HACK:?\s*(.+)', "hack"),
            (r"// TODO:?\s*(.+)", "todo"),
            (r"// FIXME:?\s*(.+)", "fixme"),
        ]
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.endswith((".py", ".js", ".ts", ".java")):
                    try:
                        with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        for pattern, rule_type in patterns:
                            for m in re.finditer(pattern, content):
                                rules.append({
                                    "rule": m.group(1).strip(),
                                    "source": "code_comment",
                                    "source_file": f,
                                    "category": rule_type,
                                    "importance": "low",
                                })
                    except Exception:
                        continue
        return rules

    def extract_from_readme(self, readme_path: str) -> List[Dict]:
        rules = []
        try:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            guidelines = [
                r'(?:coding|coding.style|code.style|开发规范|编码规范)[:\s]+(.+)',
                r'(?:naming.convention|命名规范)[:\s]+(.+)',
                r'(?:commit.message|提交信息)[:\s]+(.+)',
            ]
            for pattern in guidelines:
                for m in re.finditer(pattern, content, re.IGNORECASE):
                    rules.append({
                        "rule": m.group(1).strip()[:200],
                        "source": "readme",
                        "source_file": os.path.basename(readme_path),
                        "category": "guideline",
                        "importance": "medium",
                    })
        except Exception:
            pass
        return rules