import glob
import json
import os
import re
from typing import Dict, List
from collections import Counter


class ProjectKnowledgeScanner:
    """扫描项目目录，自动提取知识文档和规则"""

    DOC_PATTERNS = [
        "README*", "CONTRIBUTING*", "CHANGELOG*",
        "docs/**/*.md", "doc/**/*.md", "wiki/**/*.md",
        ".github/**/*.md",
        "api/**/*.md", "examples/**/*.md",
    ]

    CONFIG_PATTERNS = [
        ".eslintrc*", ".prettierrc*", ".pylintrc*",
        "tsconfig.json", "pyproject.toml",
        "package.json", "requirements.txt",
    ]

    def scan_project(self, project_path: str) -> Dict:
        if not os.path.isdir(project_path):
            return {"documents": [], "rules": [], "error": "Project path not found"}

        documents = []
        rules = []

        for pattern in self.DOC_PATTERNS:
            for file in glob.glob(os.path.join(project_path, pattern), recursive=True):
                try:
                    with open(file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        documents.append({
                            "title": os.path.basename(file),
                            "content": content,
                            "doc_type": self._detect_type(file),
                            "source_uri": os.path.relpath(file, project_path),
                            "tags": self._extract_tags(content),
                        })
                except Exception:
                    continue

        for pattern in self.CONFIG_PATTERNS:
            for file in glob.glob(os.path.join(project_path, pattern), recursive=True):
                extracted = self._extract_rules(file)
                if extracted:
                    rules.extend(extracted)

        return {
            "documents": documents,
            "rules": rules,
            "project_path": project_path,
            "document_types": Counter(d.get("doc_type") for d in documents),
            "total_docs": len(documents),
            "total_rules": len(rules),
        }

    def _detect_type(self, file_path: str) -> str:
        name = os.path.basename(file_path).lower()
        if "readme" in name:
            return "readme"
        elif "contributing" in name:
            return "contributing"
        elif "changelog" in name:
            return "changelog"
        elif "api" in file_path.lower():
            return "api_doc"
        elif ".github" in file_path:
            return "github_doc"
        return "documentation"

    def _extract_tags(self, content: str) -> List[str]:
        tags = []
        keywords = ["python", "javascript", "typescript", "go", "java", "api", "database",
                    "react", "vue", "docker", "kubernetes", "security", "testing"]
        lower = content.lower()[:500]
        for kw in keywords:
            if kw in lower:
                tags.append(kw)
        return tags[:10]

    def _extract_rules(self, file_path: str) -> List[Dict]:
        rules = []
        try:
            if file_path.endswith(".eslintrc.json") or file_path.endswith(".eslintrc"):
                with open(file_path, "r") as f:
                    config = json.load(f)
                for rule, level in config.get("rules", {}).items():
                    if isinstance(level, (list, str)):
                        severity = str(level[0]) if isinstance(level, list) else str(level)
                        if severity in ("error", "warn"):
                            rules.append({
                                "rule": f"ESLint: {rule}",
                                "source": "eslint_config",
                                "source_file": os.path.basename(file_path),
                                "category": "linting",
                                "importance": "high" if severity == "error" else "medium",
                            })
            elif "pyproject.toml" in file_path:
                content = open(file_path, "r").read()
                for m in re.finditer(r'\[tool\.(pylint|ruff|mypy)[^\]]*\]', content):
                    rules.append({
                        "rule": f"Python: {m.group(1)} config found",
                        "source": "pyproject",
                        "source_file": os.path.basename(file_path),
                        "category": m.group(1),
                        "importance": "medium",
                    })
            elif file_path.endswith("requirements.txt"):
                with open(file_path, "r") as f:
                    deps = [l.strip() for l in f if l.strip() and not l.startswith("#")]
                for dep in deps[:20]:
                    name = dep.split(">=")[0].split("==")[0].strip()
                    rules.append({
                        "rule": f"dependency: {name}",
                        "source": "requirements",
                        "source_file": os.path.basename(file_path),
                        "category": "dependency",
                        "importance": "low",
                    })
        except Exception:
            pass
        return rules