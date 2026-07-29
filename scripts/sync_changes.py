"""
Git post-commit hook helper: 自动同步本地变更到系统索引
每次 git commit 后调用，只同步变动的文件
"""

import os
import sys
import json
import subprocess
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLLER_URL = "http://192.168.0.100:8883"

CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
                   ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".idea"}


def get_changed_files():
    """Get files changed in the last commit"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            # First commit - no parent
            return []
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


def should_skip(path):
    parts = path.replace("\\", "/").split("/")
    return any(p in SKIP_DIRS or p.startswith(".") for p in parts)


def sync_code_files(file_paths):
    """Sync code files to code-index"""
    batch = []
    for fp in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, fp)
        if not os.path.exists(abs_path):
            continue
        ext = os.path.splitext(fp)[1].lower()
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp",
        }
        lang = lang_map.get(ext, "unknown")
        if lang == "unknown":
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                batch.append({"path": fp.replace("\\", "/"), "content": content, "language": lang})
        except Exception:
            pass

    if not batch:
        return

    for i in range(0, len(batch), 10):
        chunk = batch[i:i+10]
        payload = json.dumps({"capability": "code.index_files", "arguments": {"project_id": 3, "files": chunk}})
        req = urllib.request.Request(
            f"{CONTROLLER_URL}/api/tools/code-index/invoke",
            data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                r = json.loads(resp.read().decode())
                print(f"  [code] synced {len(chunk)} files")
        except Exception as e:
            print(f"  [code] sync error: {e}")


def sync_doc_files(file_paths):
    """Sync doc files to knowledge base"""
    docs = []
    for fp in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, fp)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                title = os.path.splitext(os.path.basename(fp))[0]
                docs.append({
                    "title": title, "content": content,
                    "filename": fp.replace("\\", "/"),
                    "source_uri": fp.replace("\\", "/"),
                })
        except Exception:
            pass

    if not docs:
        return

    payload = json.dumps({"auto_classify": True, "auto_create_kb": True, "documents": docs})
    req = urllib.request.Request(
        f"{CONTROLLER_URL}/api/classification/import",
        data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            r = json.loads(resp.read().decode())
            s = r.get("stored", {})
            print(f"  [doc] synced {len(docs)} files: +{s.get('knowledge',0)}kb +{s.get('rule',0)}rule")
    except Exception as e:
        print(f"  [doc] sync error: {e}")


def main():
    files = get_changed_files()
    if not files:
        print("[sync] No changed files detected or first commit")
        return

    code_files = []
    doc_files = []
    for fp in files:
        if should_skip(fp):
            continue
        ext = os.path.splitext(fp)[1].lower()
        if ext in CODE_EXTENSIONS:
            code_files.append(fp)
        elif ext in DOC_EXTENSIONS:
            doc_files.append(fp)

    if code_files:
        print(f"[sync] Syncing {len(code_files)} changed code files...")
        sync_code_files(code_files)

    if doc_files:
        print(f"[sync] Syncing {len(doc_files)} changed doc files...")
        sync_doc_files(doc_files)

    if not code_files and not doc_files:
        print("[sync] No code/doc files changed")


if __name__ == "__main__":
    main()