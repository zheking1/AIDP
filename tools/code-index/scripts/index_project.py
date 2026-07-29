#!/usr/bin/env python3
"""
AIDP Code Index Scanner
Scans local project files and sends to code-index for indexing.

Usage: python index_project.py <project_name> <project_path> [--controller-url URL] [--batch-size N]
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
    ".sql": "sql", ".sh": "shell", ".bash": "shell",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json",
    ".toml": "toml", ".xml": "xml", ".html": "html",
    ".css": "css", ".scss": "scss", ".md": "markdown",
}

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".svn", ".hg",
    "venv", "env", ".env", ".venv", "dist", "build",
    ".idea", ".vscode", ".next", ".nuxt", "coverage",
    ".mypy_cache", ".pytest_cache", "egg-info", ".tox",
    "vendor", "target", "bin", "obj",
}

MAX_FILE_SIZE = 100 * 1024  # 100KB


def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return EXTENSIONS.get(ext, "unknown")


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def scan_project(project_path: str) -> list:
    files = []
    for root, dirs, filenames in os.walk(project_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fname in filenames:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, project_path).replace("\\", "/")
            lang = detect_language(rel_path)
            if lang == "unknown":
                continue
            try:
                size = os.path.getsize(fpath)
                if size > MAX_FILE_SIZE or size == 0:
                    continue
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content.strip():
                    continue
                files.append({"path": rel_path, "content": content, "language": lang})
            except (PermissionError, OSError):
                continue
    return files


def invoke_tool(controller_url: str, capability: str, input_data: dict, api_key: str = None, max_retries: int = 3) -> dict:
    url = f"{controller_url}/api/tools/code-index/invoke"
    payload = {
        "capability": capability,
        "arguments": input_data,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    data = json.dumps(payload).encode("utf-8")
    
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 429 or "locked" in body.lower():
                wait = 2 ** attempt
                print(f"    Rate limited/locked, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            return {"success": False, "error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"    Locked error, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Max retries exceeded"}


def main():
    parser = argparse.ArgumentParser(description="AIDP Code Index Scanner")
    parser.add_argument("project_name", help="Project name")
    parser.add_argument("project_path", help="Local project path")
    parser.add_argument("--controller-url", default="http://192.168.0.100:8883", help="Controller URL")
    parser.add_argument("--batch-size", type=int, default=10, help="Files per batch")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between batches (seconds)")
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a directory")
        sys.exit(1)

    print(f"Scanning {project_path}...")
    files = scan_project(project_path)
    print(f"Found {len(files)} code files")

    if not files:
        print("No code files to index")
        sys.exit(0)

    # Create project in code-index
    print(f"Creating project '{args.project_name}'...")
    result = invoke_tool(args.controller_url, "code.create_project", {
        "name": args.project_name,
        "path": project_path,
    }, args.api_key)
    print(f"  create_project: {json.dumps(result, indent=2)}")

    project_id = None
    if isinstance(result, dict):
        output = result.get("output", result)
        if isinstance(output, dict):
            project_id = output.get("project_id") or output.get("id")
        elif isinstance(output, int):
            project_id = output
    if not project_id:
        print("Error: Could not get project_id from create_project")
        sys.exit(1)
    print(f"  project_id: {project_id}")

    # Index files in batches
    total_nodes = 0
    total_edges = 0
    total_files = 0
    for i in range(0, len(files), args.batch_size):
        batch = files[i:i + args.batch_size]
        batch_num = i // args.batch_size + 1
        total_batches = (len(files) + args.batch_size - 1) // args.batch_size
        print(f"Indexing batch {batch_num}/{total_batches} ({len(batch)} files)...")

        result = invoke_tool(args.controller_url, "code.index_files", {
            "project_id": project_id,
            "files": batch,
        }, args.api_key)

        print(f"  {json.dumps(result, indent=2)}")

        if isinstance(result, dict):
            output = result.get("output", result)
            if isinstance(output, dict):
                total_nodes += output.get("nodes_created", 0)
                total_edges += output.get("edges_created", 0)
                total_files += output.get("files_indexed", 0)
                errors = output.get("errors", [])
                if errors:
                    for e in errors:
                        print(f"  Error: {e}")

        # Delay between batches to avoid SQLite lock contention
        if i + args.batch_size < len(files):
            time.sleep(args.delay)

    print(f"\nDone! Indexed {total_files} files, {total_nodes} nodes, {total_edges} edges")
    print(f"Project ID: {project_id}")


if __name__ == "__main__":
    main()
