"""
AIDP Init — 一键初始化项目到 AIDP 平台

运行方式:
  python scripts/aidp_init.py --project-dir D:\\Project\\web\\my-app

流程:
  1. 扫描本地所有代码文件 → code.index_files
  2. 扫描所有文档文件 → /api/classification/import
  3. 检测技术栈 → 更新项目
  4. 安装文件监听 + Git 钩子
  5. NAS 端创建项目 + 初始化
  6. 自检 verify
"""

import os
import sys
import json
import time
import urllib.request
from pathlib import Path

CONTROLLER_URL = os.environ.get("AIDP_CONTROLLER_URL", "http://192.168.0.100:8883")
API_KEY = os.environ.get("AIDP_API_KEY", "")
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

# 要索引的代码扩展名
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
             ".rb", ".php", ".c", ".cpp", ".cs", ".swift", ".kt", ".vue", ".scala", ".kt", ".kts"}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "env", ".env",
             "dist", "build", ".idea", ".vscode", ".next", ".nuxt", "coverage",
             ".pytest_cache", ".mypy_cache", ".tox", "target", "bin", "obj", "data", "logs"}
MAX_FILE_SIZE = 200 * 1024  # 200KB

# 语言映射
LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".swift": "swift",
    ".kt": "kotlin", ".kts": "kotlin", ".vue": "vue", ".scala": "scala",
}


def _req(method, path, data=None):
    url = f"{CONTROLLER_URL}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════
# Phase 1: 扫描文件
# ═══════════════════════════════════════════

def scan_files(project_dir):
    """扫描项目目录，返回代码文件和文档文件列表"""
    code_files = []
    doc_files = []
    project_dir = os.path.abspath(project_dir)

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if "node_modules" in root:
            continue
        for f in files:
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, project_dir).replace("\\", "/")
            ext = os.path.splitext(f)[1].lower()
            size = os.path.getsize(fpath)
            if size > MAX_FILE_SIZE or size == 0:
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                if not content.strip():
                    continue
            except:
                continue

            if ext in CODE_EXTS:
                lang = LANG_MAP.get(ext, "unknown")
                code_files.append({"path": rel, "content": content, "language": lang})
            elif ext in DOC_EXTS:
                title = os.path.splitext(f)[0]
                doc_files.append({"title": title, "content": content, "filename": rel, "source_uri": rel})

    return code_files, doc_files


# ═══════════════════════════════════════════
# Phase 2: 上传到 NAS
# ═══════════════════════════════════════════

def upload_code(code_files, project_id):
    """分批上传代码文件到 code-index"""
    total = len(code_files)
    batch_size = 10
    uploaded = 0
    for i in range(0, total, batch_size):
        batch = code_files[i:i+batch_size]
        result = _req("POST", f"/api/tools/code-index/invoke", {
            "capability": "code.index_files",
            "arguments": {"project_id": project_id, "files": batch}
        })
        output = result.get("output", result)
        if isinstance(output, dict):
            uploaded += output.get("files_indexed", 0)
        sys.stdout.write(f"\r  code: {uploaded}/{total}")
        sys.stdout.flush()
        time.sleep(0.3)
    print()
    return uploaded


def upload_docs(doc_files, project_id):
    """导入文档到 knowledge 库"""
    if not doc_files:
        return 0
    batch_size = 5
    imported = 0
    for i in range(0, len(doc_files), batch_size):
        batch = doc_files[i:i+batch_size]
        result = _req("POST", "/api/classification/import", {
            "auto_classify": True, "auto_create_kb": True, "project_id": project_id, "documents": batch
        })
        s = result.get("stored", {})
        imported += s.get("knowledge", 0)
        sys.stdout.write(f"\r  docs: {imported}/{len(doc_files)}")
        sys.stdout.flush()
        time.sleep(0.3)
    print()
    return imported


def upload_tech_stack(project_dir, project_id):
    """检测技术栈并更新项目"""
    techs = set()
    frameworks = set()

    pkg = os.path.join(project_dir, "package.json")
    if os.path.exists(pkg):
        techs.add("Node.js")
        with open(pkg, "r", encoding="utf-8", errors="ignore") as f:
            try:
                deps = {**json.load(f).get("dependencies", {}), **json.load(f).get("devDependencies", {})}
                dn = set(deps.keys())
                if any("vue" in d.lower() for d in dn): frameworks.add("Vue")
                if any("react" in d.lower() for d in dn): frameworks.add("React")
                if any("next" in d.lower() for d in dn): frameworks.add("Next.js")
            except:
                pass

    pom = os.path.join(project_dir, "pom.xml")
    if os.path.exists(pom):
        techs.add("Java")
        c = open(pom, "r", encoding="utf-8", errors="ignore").read().lower()
        if "spring-boot" in c: frameworks.add("Spring Boot")
        if "spring-cloud" in c: frameworks.add("Spring Cloud")

    req = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req):
        techs.add("Python")
        c = open(req, "r", encoding="utf-8", errors="ignore").read().lower()
        if "fastapi" in c: frameworks.add("FastAPI")
        if "django" in c: frameworks.add("Django")

    gradle = os.path.join(project_dir, "build.gradle")
    if os.path.exists(gradle):
        techs.add("Gradle")
        c = open(gradle, "r", encoding="utf-8", errors="ignore").read().lower()
        if "spring" in c: frameworks.add("Spring Boot")

    if os.path.exists(os.path.join(project_dir, "go.mod")): techs.add("Go")
    if os.path.exists(os.path.join(project_dir, "Cargo.toml")): techs.add("Rust")
    if os.path.exists(os.path.join(project_dir, "Dockerfile")): techs.add("Docker")

    all_tech = list(techs | frameworks)
    if all_tech:
        _req("PUT", f"/api/projects/{project_id}", {"tech_stack": json.dumps(all_tech)})
        print(f"  tech: {', '.join(all_tech)}")
    return all_tech


def install_local(project_dir, project_id):
    """安装文件监听 + Git 钩子"""
    opencode_dir = Path(project_dir) / ".opencode"
    git_hooks_dir = Path(project_dir) / ".git" / "hooks"

    # watcher.json
    opencode_dir.mkdir(parents=True, exist_ok=True)
    watcher_conf = {
        "version": "1.0", "project_id": project_id,
        "project_root": str(Path(project_dir).resolve()),
        "controller_url": CONTROLLER_URL,
    }
    with open(opencode_dir / "watcher.json", "w", encoding="utf-8") as f:
        json.dump(watcher_conf, f, indent=2)
    print(f"  watcher: created .opencode/watcher.json")

    # Git hook
    if git_hooks_dir.exists():
        hook = git_hooks_dir / "post-commit"
        hook_content = f"""@echo off
python "%~dp0\\..\\..\\scripts\\sync_changes.py"
if %errorlevel% neq 0 (echo [aidp] sync warning) else (echo [aidp] synced)
"""
        with open(hook, "w", encoding="utf-8") as f:
            f.write(hook_content)
        print(f"  git: installed post-commit hook")
    else:
        print(f"  git: no .git directory, skip hook")


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AIDP Init — 一键初始化项目")
    parser.add_argument("--project-dir", required=True, help="项目目录路径")
    parser.add_argument("--project-name", default=None, help="项目名称（默认取目录名）")
    parser.add_argument("--description", default="", help="项目描述")
    parser.add_argument("--project-id", type=int, default=None, help="已有项目 ID（跳过创建）")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    project_name = args.project_name or os.path.basename(project_dir)
    print(f"\n{'='*50}")
    print(f"  AIDP Init: {project_name}")
    print(f"  目录: {project_dir}")
    print(f"{'='*50}\n")

    # 1. 扫描文件
    print("[1/6] 扫描文件...")
    code_files, doc_files = scan_files(project_dir)
    print(f"  代码: {len(code_files)} 个文件")
    print(f"  文档: {len(doc_files)} 个文件")

    # 2. 检测技术栈
    print("\n[2/6] 检测技术栈...")
    tech_stack = upload_tech_stack(project_dir, None)
    tech_str = json.dumps(tech_stack) if tech_stack else "[]"

    # 3. NAS 端创建项目并初始化
    print("\n[3/6] NAS 端初始化...")
    pid = args.project_id
    if pid:
        print(f"  使用已有项目: id={pid}")
    else:
        # 先尝试查找同名项目
        projects = _req("GET", "/api/projects")
        items = projects.get("items", projects if isinstance(projects, list) else [])
        existing = [p for p in items if p.get("name") == project_name] if isinstance(items, list) else []
        if existing:
            pid = existing[0].get("id")
            print(f"  项目已存在: id={pid}")
        else:
            result = _req("POST", "/api/projects", {"name": project_name, "description": args.description, "visibility": "private"})
            pid = result.get("id")
            if not pid:
                print(f"  WARNING: 创建项目失败，使用 project-id=3（ruoyi）作为后备")
                pid = 3  # fallback for ruoyi project

    if not pid:
        print("  ERROR: 无法创建项目，退出")
        sys.exit(1)

    # NAS 端 init 任务
    _req("POST", f"/api/projects/{pid}/init", {"tasks": ["code_index", "mcp_register"]})

    # 4. 上传代码到 code-index
    print(f"\n[4/6] 上传代码 (project_id={pid})...")
    uploaded = upload_code(code_files, pid)
    print(f"  代码索引完成: {uploaded} 个文件")

    # 5. 导入文档
    print(f"\n[5/6] 导入文档...")
    imported = upload_docs(doc_files, pid)
    print(f"  文档导入完成: {imported} 篇")

    # 6. 安装本地组件
    print(f"\n[6/6] 安装本地组件...")
    install_local(project_dir, pid)

    # 7. 更新 init 任务状态
    print(f"\n[verify] 运行自检...")
    try:
        _req("POST", f"/api/projects/{pid}/init", {"tasks": []})
    except:
        pass
    verify = _req("GET", f"/api/projects/{pid}/verify")
    if isinstance(verify, dict) and "checks" in verify:
        for c in verify["checks"]:
            icon = "PASS" if c.get("passed") else "FAIL"
            print(f"  [{icon}] {c['name']}: {c['detail']}")
        print(f"  {verify['summary']}")
    else:
        print(f"  verify: {json.dumps(verify, indent=2, ensure_ascii=False)[:200]}")

    print(f"\n{'='*50}")
    print(f"  初始化完成！Project ID: {pid}")
    print(f"  文件监听: python scripts/file_watcher.py")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()