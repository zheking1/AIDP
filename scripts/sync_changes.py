"""
Git post-commit hook helper: 自动同步本地变更到系统索引
每次 git commit 后调用，只同步变动的文件（差量更新）

安装: aidp_init.py 自动写入 .git/hooks/post-commit
手动: python scripts/sync_changes.py --project-id 42
"""

import os
import re
import sys
import json
import argparse
import subprocess
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLLER_URL = os.environ.get("AIDP_CONTROLLER_URL", "http://192.168.0.100:8883")

CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
                   ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".idea"}


def load_project_id():
    config_path = os.path.join(PROJECT_ROOT, ".opencode", "watcher.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
                return config.get("project_id", 0)
        except Exception:
            pass
    return 0


def get_changed_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            return []
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


def should_skip(path):
    parts = path.replace("\\", "/").split("/")
    return any(p in SKIP_DIRS or p.startswith(".") for p in parts)


def get_token():
    cfg = os.path.join(PROJECT_ROOT, ".opencode", "watcher.json")
    if os.path.exists(cfg):
        try:
            with open(cfg) as f:
                return json.load(f).get("api_key", "")
        except Exception:
            pass
    return os.environ.get("AIDP_API_KEY", "")


def sync_code_files(file_paths, project_id):
    token = get_token()
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

    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-API-Key"] = token

    for i in range(0, len(batch), 10):
        chunk = batch[i:i+10]
        payload = json.dumps({"capability": "code.index_files", "arguments": {"project_id": project_id, "files": chunk}})
        req = urllib.request.Request(
            f"{CONTROLLER_URL}/api/tools/code-index/invoke",
            data=payload.encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                print(f"  [code] synced {len(chunk)} files -> project {project_id}")
        except Exception as e:
            print(f"  [code] sync error: {e}")


def sync_doc_files(file_paths):
    token = get_token()
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

    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-API-Key"] = token

    payload = json.dumps({"auto_classify": True, "auto_create_kb": True, "documents": docs})
    req = urllib.request.Request(
        f"{CONTROLLER_URL}/api/classification/import",
        data=payload.encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"  [doc] synced {len(docs)} files")
    except Exception as e:
        print(f"  [doc] sync error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sync changed files from git commit to AIDP index")
    parser.add_argument("--project-id", "-p", type=int, default=0, help="AIDP project ID")
    args = parser.parse_args()

    project_id = args.project_id or load_project_id()
    if not project_id:
        print("[sync] ERROR: No project_id. Provide --project-id or ensure .opencode/watcher.json exists")
        sys.exit(1)

    files = get_changed_files()
    if not files:
        print("[sync] No changed files detected or first commit")
        return

    code_files, doc_files = [], []
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
        sync_code_files(code_files, project_id)
    if doc_files:
        print(f"[sync] Syncing {len(doc_files)} changed doc files...")
        sync_doc_files(doc_files)
    if not code_files and not doc_files:
        print("[sync] No code/doc files changed")


if __name__ == "__main__":
    main()