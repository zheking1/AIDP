from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx, os, json

app = FastAPI(title="Project Importer", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

AIDP_BASE = "http://127.0.0.1"
CONTROLLER = f"{AIDP_BASE}:8883"
CODE_INDEX = f"{AIDP_BASE}:18086"
KNOWLEDGE = f"{AIDP_BASE}:18081"
MEMORY = f"{AIDP_BASE}:18085"
SKILLROUTER = f"{AIDP_BASE}:8788"

FRAMEWORK_SIGNALS = {
    "FastAPI": ["requirements.txt", "fastapi", "uvicorn"],
    "Spring Boot": ["pom.xml", "Application.java", "application.yml"],
    "React": ["package.json", "react", "tsx"],
    "Vue": ["vue", "package.json"],
    "Django": ["manage.py", "settings.py"],
    "Flask": ["requirements.txt", "flask"],
    "Go Gin": ["go.mod", "gin"],
    "Rust Actix": ["Cargo.toml", "actix"],
    "NestJS": ["nest-cli.json", "@nestjs"],
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/onboarding/scan")
async def onboarding_scan(path: str):
    """Step 2: 扫描项目，自动识别语言、框架、文档、配置"""
    files = _scan_directory(path)
    groups = _group_by_type(files)
    language = _detect_language(files)
    framework = _detect_framework(path, files)

    return {
        "path": path,
        "language": language,
        "framework": framework,
        "total_files": len(files),
        "code_files": len(groups.get("code", [])),
        "doc_files": len(groups.get("doc", [])) + len(groups.get("doc_files", [])),
        "config_files": len(groups.get("config", [])),
        "script_files": len(groups.get("script", [])),
        "doc_preview": [f["path"] for f in groups.get("doc", [])[:5]],
        "config_preview": [f["path"] for f in groups.get("config", [])[:5]],
    }


@app.post("/api/onboarding/import")
async def onboarding_import(request: Request):
    """Step 3: 完整导入"""
    body = await request.json()
    project_path = body.get("path", "")
    project_name = body.get("name", "")
    project_type = body.get("type", "python")

    if not project_path or not project_name:
        raise HTTPException(400, "path and name are required")

    result = {"steps": [], "errors": [], "progress": 0}

    async def report(step_name, progress_pct):
        result["steps"].append({"step": step_name, "done": True})
        result["progress"] = progress_pct

    # Create project
    pid = await _create_project(project_name, project_type)
    await report("Create project", 10)

    # Scan
    files = _scan_directory(project_path)
    groups = _group_by_type(files)
    language = _detect_language(files)
    framework = _detect_framework(project_path, files)
    await report("Scan directory", 20)

    # Index code
    try:
        if groups["code"]:
            await _index_code(pid, project_path, project_name)
        await report("Index code", 40)
    except Exception as e:
        await report("Index code (skipped)", 40)

    # Import docs
    doc_count = 0
    for f in groups.get("doc", [])[:50]:
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()[:30000]
        except:
            continue
        async with httpx.AsyncClient() as c:
            await c.post(f"{KNOWLEDGE}/api/documents", json={
                "workspace_id": "default", "title": f["path"], "doc_type": "markdown",
                "content": content, "project_id": str(pid),
            })
            doc_count += 1
    await report("Import docs", 60)

    # Import configs
    config_count = 0
    for f in groups.get("config", [])[:20]:
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                val = fh.read()[:500]
        except:
            val = ""
        env = "prod" if "prod" in f["path"].lower() else "test" if "test" in f["path"].lower() else "dev"
        async with httpx.AsyncClient() as c:
            await c.post(f"{CONTROLLER}/api/projects/{pid}/configs/",
                         json={"env_type": env, "config_key": f["path"], "config_value": val})
            config_count += 1
    await report("Import configs", 75)

    # Create memories
    memories = [
        ("项目技术栈", f"{project_name} 技术栈: {language}, 框架: {framework}", "semantic"),
        ("项目结构", f"{project_name} 包含 {len(groups.get('code',[]))} 个源码文件, {doc_count} 个文档", "semantic"),
    ]
    for title, content, tier in memories:
        async with httpx.AsyncClient() as c:
            await c.post(f"{MEMORY}/api/memory", json={
                "project": project_name, "category": "architecture",
                "title": title, "content": content, "memory_tier": tier, "source_type": "auto",
            })
    await report("Create memories", 90)

    # Summary
    await report("Complete", 100)
    result["summary"] = {
        "project_id": pid,
        "project_name": project_name,
        "language": language,
        "framework": framework,
        "code_files": len(groups.get("code", [])),
        "doc_files": doc_count,
        "config_files": config_count,
        "total_files": len(files),
    }
    return JSONResponse(result)


def _detect_language(files):
    ext_counts = {}
    for f in files:
        ext = f["ext"]
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
    ext_to_lang = {".py": "python", ".java": "java", ".ts": "typescript", ".tsx": "typescript",
                   ".js": "javascript", ".vue": "vue", ".go": "go", ".rs": "rust"}
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        if ext in ext_to_lang:
            return ext_to_lang[ext]
    return "unknown"


def _detect_framework(path, files):
    file_names = set(f["path"].split("/")[-1].lower() for f in files)
    for root, dirs, filenames in os.walk(path):
        file_names.update(f.lower() for f in filenames)
        break
    for fw, signals in FRAMEWORK_SIGNALS.items():
        if any(s.lower() in file_names for s in signals):
            return fw
    return "unknown"


@app.post("/api/import/project")
async def import_project(request: Request):
    """一键导入：扫描项目 → 索引代码 → 导入文档 → 配置 → skill/rule"""
    body = await request.json()
    project_path = body.get("path", "")
    project_name = body.get("name", "")
    project_type = body.get("type", "java")

    if not project_path or not project_name:
        raise HTTPException(400, "path and name are required")

    result = {"steps": [], "errors": []}

    # Step 1: Create project in Controller
    project_id = await _step(result, "Create project", _create_project, project_name, project_type)

    # Step 2: Scan directory structure
    files = await _step(result, "Scan directory", _scan_directory, project_path)
    files_by_type = _group_by_type(files)

    # Step 3: Index code in Code Index
    await _step(result, "Index code", _index_code, project_id, project_path, project_name)

    # Step 4: Import README/markdown docs to Knowledge
    await _step(result, "Import docs", _import_docs, project_id, project_path, files_by_type)

    # Step 5: Import configs (application.yml/.env/.properties) to Controller
    await _step(result, "Import configs", _import_configs, project_id, project_path, files_by_type)

    # Step 6: Import scripts/templates to Asset Tool
    await _step(result, "Import assets", _import_assets, project_id, project_path, files_by_type)

    # Summary
    result["summary"] = {
        "project_id": project_id,
        "project_name": project_name,
        "total_steps": len(result["steps"]),
        "total_errors": len(result["errors"]),
        "files_found": len(files),
        "code_files": len(files_by_type.get("code", [])),
        "doc_files": len(files_by_type.get("doc", [])),
        "config_files": len(files_by_type.get("config", [])),
        "script_files": len(files_by_type.get("script", [])),
    }
    return JSONResponse(result)


@app.get("/api/scan")
async def scan_project(path: str):
    files = _scan_directory(path)
    return JSONResponse({
        "path": path,
        "total_files": len(files),
        "by_type": _group_by_type(files),
    })


import httpx
import os
import json


async def _step(result, name, fn, *args):
    try:
        r = await fn(*args)
        result["steps"].append({"step": name, "status": "ok", "result": r})
        return r
    except Exception as e:
        result["steps"].append({"step": name, "status": "error", "error": str(e)})
        result["errors"].append(str(e))
        return None


async def _create_project(name, ptype):
    async with httpx.AsyncClient() as c:
        await c.post(f"{CONTROLLER}/api/auth/login", json={"username": os.environ.get("ADMIN_USERNAME", "admin"), "password": os.environ.get("ADMIN_PASSWORD", "admin123")})
        r = await c.post(f"{CONTROLLER}/api/projects/", json={"name": name, "description": "Imported project", "type": ptype})
        r.raise_for_status()
        return r.json()["id"]


def _scan_directory(path):
    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in filenames:
            if f.startswith('.'):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, path)
            ext = os.path.splitext(f)[1].lower()
            files.append({"path": rel, "full_path": full, "ext": ext, "size": os.path.getsize(full)})
        if len(files) > 2000:
            break
    return files


def _group_by_type(files):
    CODE_EXTS = {".java", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".cpp", ".c", ".h", ".vue", ".kt"}
    DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}
    CONFIG_EXTS = {".yml", ".yaml", ".properties", ".env", ".json", ".toml", ".ini", ".cfg", ".xml"}
    SCRIPT_EXTS = {".sh", ".bat", ".ps1", ".sql", ".dockerfile"}
    groups = {"code": [], "doc": [], "config": [], "script": [], "other": []}
    for f in files:
        if f["ext"] in CODE_EXTS:
            groups["code"].append(f)
        elif f["ext"] in DOC_EXTS:
            groups["doc"].append(f)
        elif f["ext"] in CONFIG_EXTS:
            groups["config"].append(f)
        elif f["ext"] in SCRIPT_EXTS:
            groups["script"].append(f)
        else:
            groups["other"].append(f)
    return groups


async def _index_code(project_id, path, name):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{CODE_INDEX}/api/projects", json={"name": name, "path": path})
        r.raise_for_status()
        ci_id = r.json()["id"]
        r = await c.post(f"{CODE_INDEX}/api/index/directory", json={"project_id": ci_id, "dir_path": path})
        r.raise_for_status()
        return {"code_index_id": ci_id, **r.json()}


async def _import_docs(project_id, path, groups):
    count = 0
    for f in groups.get("doc", [])[:50]:
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()[:50000]
        except:
            continue
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{KNOWLEDGE}/api/documents", json={
                "workspace_id": "default",
                "document_id": str(project_id or ""),
                "title": f["path"],
                "doc_type": "markdown",
                "content": content,
                "source_uri": f["path"],
                "project_id": str(project_id),
            })
            if r.status_code < 400:
                count += 1
    return {"docs_imported": count}


async def _import_configs(project_id, path, groups):
    count = 0
    for f in groups.get("config", [])[:30]:
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()[:5000]
        except:
            content = ""
        env = "dev"
        if "prod" in f["path"].lower():
            env = "prod"
        elif "test" in f["path"].lower():
            env = "test"
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{CONTROLLER}/api/projects/{project_id}/configs", json={
                "env_type": env,
                "config_key": f["path"],
                "config_value": content[:500],
            })
            if r.status_code < 400:
                count += 1
    return {"configs_imported": count}


async def _import_assets(project_id, path, groups):
    count = 0
    for f in groups.get("script", [])[:20]:
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()[:10000]
        except:
            continue
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{AIDP_BASE}:18082/api/assets", json={
                "name": f["path"],
                "content": content,
                "asset_type": "script",
                "tags": [f["ext"]],
                "project_id": str(project_id),
            })
            if r.status_code < 400:
                count += 1
    return {"assets_imported": count}