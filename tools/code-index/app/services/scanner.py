import os
import re
from typing import Dict, List, Optional


LANGUAGE_EXTENSIONS = {
    "java": [".java"],
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "go": [".go"],
    "rust": [".rs"],
}

FRAMEWORK_PATTERNS = {
    "spring_boot": ["pom.xml", "build.gradle", "application.yml", "application.properties", "@SpringBootApplication"],
    "fastapi": ["requirements.txt", "main.py", "fastapi", "uvicorn"],
    "nestjs": ["package.json", "@nestjs", "nest-cli.json"],
}


class Scanner:
    def scan_directory(self, path: str) -> Dict:
        result = {
            "path": path,
            "language": self._detect_language(path),
            "framework": self._detect_framework(path),
            "files": [],
            "modules": [],
        }
        if not os.path.isdir(path):
            return result

        for root, dirs, files in os.walk(path):
            # Skip hidden dirs and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', '__pycache__', 'target', 'build')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                for lang, extensions in LANGUAGE_EXTENSIONS.items():
                    if ext in extensions:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, path)
                        result["files"].append({
                            "path": rel_path,
                            "full_path": full_path,
                            "language": lang,
                            "size": os.path.getsize(full_path),
                        })
                        break

        result["modules"] = self._detect_modules(path, result["files"])
        return result

    def _detect_language(self, path: str) -> str:
        for root, _, files in os.walk(path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                for lang, extensions in LANGUAGE_EXTENSIONS.items():
                    if ext in extensions:
                        return lang
            break
        return "unknown"

    def _detect_framework(self, path: str) -> str:
        for root, _, files in os.walk(path):
            file_set = set(files)
            for fw, patterns in FRAMEWORK_PATTERNS.items():
                for p in patterns:
                    if p in file_set:
                        return fw
            break
        return "unknown"

    def _detect_modules(self, path: str, files: List[Dict]) -> List[Dict]:
        modules = []
        seen = set()
        for f in files:
            parts = f["path"].split(os.sep)
            if len(parts) > 1:
                mod = parts[0]
                if mod not in seen:
                    seen.add(mod)
                    mod_files = [ff for ff in files if ff["path"].startswith(mod + os.sep)]
                    modules.append({
                        "name": mod,
                        "file_count": len(mod_files),
                        "path": mod,
                    })
        return modules
