import io
import json
import tarfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select

from app.tools.skill_router.db.init_db import get_session
from app.tools.skill_router.db.models import Skill, SkillFile
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api")


# ------ CLI Install Script ------

CLI_INSTALL_SH = r'''#!/usr/bin/env bash
# SkillRouter CLI Installer
set -e

SERVER="${1:-http://localhost:8788}"
INSTALL_DIR="${2:-$HOME/.skillcli}"

echo "Installing SkillRouter CLI..."
echo "  Server: $SERVER"
echo "  Target: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR/bin"

# Download srcli.py from the server
if command -v curl &>/dev/null; then
  curl -sSL "$SERVER/api/cli/srcli.py" -o "$INSTALL_DIR/bin/srcli.py"
elif command -v wget &>/dev/null; then
  wget -q "$SERVER/api/cli/srcli.py" -O "$INSTALL_DIR/bin/srcli.py"
else
  echo "Error: need curl or wget"
  exit 1
fi

chmod +x "$INSTALL_DIR/bin/srcli.py"

# Create wrapper script
cat > "$INSTALL_DIR/bin/srcli" << 'WRAPPER'
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/srcli.py" "$@"
WRAPPER
chmod +x "$INSTALL_DIR/bin/srcli"

# Add to PATH in shell config
SHELL_RC="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then SHELL_RC="$HOME/.zshrc"; fi
if ! grep -q "skillcli/bin" "$SHELL_RC" 2>/dev/null; then
  echo "export PATH=\"\$PATH:$INSTALL_DIR/bin\"" >> "$SHELL_RC"
  echo "Added $INSTALL_DIR/bin to PATH in $SHELL_RC"
fi

echo "Done! Run: source $SHELL_RC && srcli config --server $SERVER"
'''


@router.get("/cli/install.sh")
async def api_cli_install_sh():
    return Response(
        content=CLI_INSTALL_SH,
        media_type="text/x-shellscript",
        headers={"Content-Disposition": "attachment; filename=install.sh"},
    )


@router.get("/cli/srcli.py")
async def api_cli_srcli_py():
    return Response(
        content=open("cli/srcli.py", encoding="utf-8").read(),
        media_type="text/x-python",
        headers={"Content-Disposition": "attachment; filename=srcli.py"},
    )


def _check_auth(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user


async def _user_id(user: dict, db=None) -> uuid.UUID:
    try:
        return uuid.UUID(user.get("id", ""))
    except (ValueError, AttributeError):
        if db:
            from app.tools.skill_router.config import settings
            from app.tools.skill_router.db.models import User
            result = await db.execute(select(User).where(User.username == settings.admin_username))
            admin = result.scalar_one_or_none()
            if admin:
                return admin.id
        return uuid.UUID(int=1)


# ------ Skill CRUD API ------


@router.get("/skills")
async def api_list_skills(request: Request, limit: int = 1000):
    async with get_session() as db:
        query = select(Skill).where(Skill.is_active == True).options(selectinload(Skill.group)).order_by(Skill.updated_at.desc()).limit(limit)
        result = await db.execute(query)
        skills = result.scalars().all()
    return {
        "items": [
            {
                "id": str(s.id),
                "name": s.name,
                "version": s.version,
                "tags": s.tags or [],
                "description": s.description or "",
                "review_status": s.review_status,
                "group_id": str(s.group_id) if s.group_id else None,
                "group_name": s.group.name if s.group else None,
                "executable": bool(s.exec_config and s.exec_config.get("executable")),
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            }
            for s in skills
        ]
    }


# MUST be before {skill_id} routes to avoid path conflict
@router.get("/skills/search")
async def api_search_skills(q: str = "", tag: str = ""):
    async with get_session() as db:
        query = select(Skill).where(Skill.is_active == True)
        if q:
            query = query.where(Skill.name.ilike(f"%{q}%"))
        if tag:
            query = query.where(Skill.tags.any(tag))
        query = query.options(selectinload(Skill.files)).order_by(Skill.updated_at.desc()).limit(50)
        result = await db.execute(query)
        skills = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "version": s.version,
            "tags": s.tags or [],
            "description": s.description or "",
            "review_status": s.review_status,
            "executable": bool(s.exec_config and s.exec_config.get("executable")),
            "auto_update": bool(s.exec_config and s.exec_config.get("auto_update", True)),
            "updated_at": s.updated_at.isoformat() if s.updated_at else "",
        }
        for s in skills
    ]


@router.post("/skills/create")
async def api_create_skill(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        allowed_roles = data.get("allowed_roles")
        if isinstance(allowed_roles, str):
            allowed_roles = [r.strip() for r in allowed_roles.split(",") if r.strip()] or None
        scope = data.get("scope", "private")
        sensitive = data.get("sensitive", False)
        instruction = data.get("instruction")
        # Check name uniqueness
        name = data.get("name", "untitled").strip()
        user_id = await _user_id(user, db=db)
        existing = await db.execute(select(Skill).where(Skill.user_id == user_id, Skill.name == name))
        if existing.scalar_one_or_none():
            return JSONResponse({"error": "Skill name already exists"}, status_code=400)
        skill = Skill(
            name=name,
            content=data.get("content", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            version=1,
            review_status="pending",
            user_id=await _user_id(user, db=db),
            allowed_roles=allowed_roles,
            scope=scope,
            sensitive=sensitive,
            instruction=instruction,
        )
        db.add(skill)
        await db.flush()

        exec_config = data.get("exec_config")
        if exec_config and exec_config.get("executable"):
            skill.exec_config = exec_config

        for idx, f in enumerate(data.get("files", [])):
            sf = SkillFile(
                skill_id=skill.id,
                path=f.get("path", f"file_{idx}"),
                content=f.get("content", ""),
                language=f.get("language", "text"),
                is_entry=f.get("is_entry", idx == 0),
                sort_order=f.get("sort_order", idx),
            )
            db.add(sf)

        await db.commit()
        return {"ok": True, "id": str(skill.id), "name": skill.name}


# ------ Skill Files API ------

@router.get("/skills/{skill_id}")
async def api_get_skill(skill_id: str):
    async with get_session() as db:
        result = await db.execute(select(Skill).options(selectinload(Skill.files)).where(Skill.id == uuid.UUID(skill_id)))
        skill = result.scalars().first()
        if not skill:
            return JSONResponse({"error": "not found"}, status_code=404)
        return skill.to_dict()


@router.get("/skills/{skill_id}/files")
async def api_get_files(skill_id: str):
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill:
            return JSONResponse({"error": "not found"}, status_code=404)
        return [f.to_dict() for f in skill.files]


@router.post("/skills/{skill_id}/files")
async def api_save_files(skill_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill:
            return JSONResponse({"error": "not found"}, status_code=404)
        # Delete existing files
        for f in skill.files:
            await db.delete(f)
        # Insert new files
        for idx, f in enumerate(data.get("files", [])):
            sf = SkillFile(
                skill_id=skill.id,
                path=f.get("path", f"file_{idx}"),
                content=f.get("content", ""),
                language=f.get("language", "text"),
                is_entry=f.get("is_entry", idx == 0),
                sort_order=f.get("sort_order", idx),
            )
            db.add(sf)
        await db.commit()
        await db.refresh(skill)
        return {"ok": True, "count": len(data.get("files", []))}


@router.post("/skills/{skill_id}/exec-config")
async def api_save_exec_config(skill_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill:
            return JSONResponse({"error": "not found"}, status_code=404)
        # Validate exec_config
        cfg = {
            "executable": data.get("executable", False),
            "runtime": data.get("runtime", "python3"),
            "entry": data.get("entry", ""),
            "cmd_template": data.get("cmd_template", ""),
            "timeout_secs": data.get("timeout_secs", 60),
            "auto_update": data.get("auto_update", True),
            "cleanup": data.get("cleanup", True),
            "params": data.get("params", {}),
        }
        skill.exec_config = cfg
        await db.commit()
        return {"ok": True, "exec_config": cfg}


# ------ Package API ------

@router.get("/skills/{skill_id}/package")
async def api_download_package(skill_id: str):
    async with get_session() as db:
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill:
            return JSONResponse({"error": "not found"}, status_code=404)

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            meta = {
                "id": str(skill.id),
                "name": skill.name,
                "version": skill.version,
                "description": skill.description or "",
                "tags": skill.tags or [],
                "exec_config": skill.exec_config,
                "review_status": skill.review_status,
                "created_at": skill.created_at.isoformat() if skill.created_at else "",
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else "",
            }
            meta_bytes = json.dumps(meta, indent=2).encode()
            info = tarfile.TarInfo(name="meta.json")
            info.size = len(meta_bytes)
            tar.addfile(info, io.BytesIO(meta_bytes))

            for f in skill.files:
                content = f.content.encode() if f.content else b""
                info = tarfile.TarInfo(name=f"files/{f.path}")
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))

        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/gzip",
            headers={
                "Content-Disposition": f'attachment; filename="{skill.name.replace(" ", "_")}.tar.gz"',
                "X-Skill-Name": skill.name,
                "X-Skill-Version": str(skill.version),
            },
        )


@router.post("/skills/upload")
async def api_upload_package(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.body()
    buf = io.BytesIO(body)
    skill_id = None
    name = "uploaded_skill"
    version = 1
    description = ""
    tags = []
    exec_config = None
    files = []

    try:
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            meta_file = tar.extractfile("meta.json")
            if meta_file:
                meta = json.loads(meta_file.read())
                name = meta.get("name", name)
                version = meta.get("version", 1)
                description = meta.get("description", "")
                tags = meta.get("tags", [])
                exec_config = meta.get("exec_config")

            for m in tar.getmembers():
                if m.name.startswith("files/") and m.isfile():
                    f = tar.extractfile(m)
                    content = f.read().decode() if f else ""
                    path = m.name[len("files/"):]
                    ext = path.split(".")[-1] if "." in path else "text"
                    lang_map = {"py": "python", "sh": "bash", "js": "javascript", "yaml": "yaml", "yml": "yaml", "sql": "sql", "json": "json", "md": "markdown", "txt": "text"}
                    files.append({"path": path, "content": content, "language": lang_map.get(ext, "text"), "is_entry": len(files) == 0})
    except Exception as e:
        return JSONResponse({"error": f"invalid package: {e}"}, status_code=400)

    async with get_session() as db:
        skill = Skill(
            name=name,
            content=description or name,
            tags=tags,
            description=description,
            version=version,
            exec_config=exec_config,
            user_id=await _user_id(user, db=db),
            review_status="pending",
        )
        db.add(skill)
        await db.flush()

        for idx, f in enumerate(files):
            sf = SkillFile(
                skill_id=skill.id,
                path=f["path"],
                content=f["content"],
                language=f.get("language", "text"),
                is_entry=f.get("is_entry", idx == 0),
                sort_order=idx,
            )
            db.add(sf)

        await db.commit()
        skill_id = str(skill.id)

    return {"ok": True, "id": skill_id, "name": name, "version": version, "files": len(files)}


# ------ Skill Groups API ------

@router.get("/skill-groups")
async def list_skill_groups(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with get_session() as db:
        from app.tools.skill_router.db.models import SkillGroup, Skill
        from sqlalchemy import func
        user_id = await _user_id(user, db=db)
        groups = (await db.execute(select(SkillGroup).where(SkillGroup.user_id == user_id).order_by(SkillGroup.sort_order))).scalars().all()
        # count skills per group
        skill_counts = (await db.execute(
            select(Skill.group_id, func.count(Skill.id)).where(Skill.user_id == user_id, Skill.group_id.isnot(None)).group_by(Skill.group_id)
        )).all()
        count_map = {str(gid): cnt for gid, cnt in skill_counts}
        return {"items": [
            {"id": str(g.id), "name": g.name, "parent_id": str(g.parent_id) if g.parent_id else None, 
             "sort_order": g.sort_order, "skill_count": count_map.get(str(g.id), 0)}
            for g in groups
        ]}


@router.post("/skill-groups")
async def create_skill_group(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        from app.tools.skill_router.db.models import SkillGroup
        user_id = await _user_id(user, db=db)
        name = data.get("name", "").strip()
        parent_id = uuid.UUID(data["parent_id"]) if data.get("parent_id") else None
        # Check name uniqueness
        existing = await db.execute(select(SkillGroup).where(
            SkillGroup.user_id == user_id, SkillGroup.name == name, SkillGroup.parent_id == parent_id
        ))
        if existing.scalar_one_or_none():
            return JSONResponse({"error": "Group name already exists"}, status_code=400)
        g = SkillGroup(user_id=user_id, name=name, parent_id=parent_id, sort_order=data.get("sort_order", 0))
        db.add(g)
        await db.commit()
        await db.refresh(g)
    return {"ok": True, "id": str(g.id)}


@router.patch("/skill-groups/{group_id}")
async def update_skill_group(group_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        from app.tools.skill_router.db.models import SkillGroup
        user_id = await _user_id(user, db=db)
        g = await db.get(SkillGroup, uuid.UUID(group_id))
        if not g or g.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=4040)
        if "name" in data: g.name = data["name"].strip()
        if "parent_id" in data: g.parent_id = uuid.UUID(data["parent_id"]) if data["parent_id"] else None
        if "sort_order" in data: g.sort_order = data["sort_order"]
        await db.commit()
    return {"ok": True}


@router.delete("/skill-groups/{group_id}")
async def delete_skill_group(group_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with get_session() as db:
        from app.tools.skill_router.db.models import SkillGroup, Skill
        user_id = await _user_id(user, db=db)
        g = await db.get(SkillGroup, uuid.UUID(group_id))
        if not g or g.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=404)
        # check for children
        children = (await db.execute(select(SkillGroup).where(SkillGroup.parent_id == g.id))).scalars().all()
        if children:
            return JSONResponse({"error": "Group has children, delete them first"}, status_code=400)
        # ungroup skills in this group
        skills = (await db.execute(select(Skill).where(Skill.group_id == g.id))).scalars().all()
        for skill in skills:
            skill.group_id = None
        await db.delete(g)
        await db.commit()
    return {"ok": True}


@router.post("/skills/{skill_id}/move")
async def move_skill_to_group(skill_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    group_id = data.get("group_id")
    async with get_session() as db:
        from app.tools.skill_router.db.models import Skill, SkillGroup
        user_id = await _user_id(user, db=db)
        skill = await db.get(Skill, uuid.UUID(skill_id))
        if not skill or skill.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=404)
        if group_id:
            g = await db.get(SkillGroup, uuid.UUID(group_id))
            if not g or g.user_id != user_id:
                return JSONResponse({"error": "group not found"}, status_code=404)
            skill.group_id = uuid.UUID(group_id)
        else:
            skill.group_id = None
        await db.commit()
    return {"ok": True}


# ------ Rule Groups API ------

@router.get("/rule-groups")
async def list_rule_groups(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with get_session() as db:
        from app.tools.skill_router.db.models import RuleGroup, Rule
        from sqlalchemy import func
        user_id = await _user_id(user, db=db)
        groups = (await db.execute(select(RuleGroup).where(RuleGroup.user_id == user_id).order_by(RuleGroup.sort_order))).scalars().all()
        # count rules per group
        rule_counts = (await db.execute(
            select(Rule.group_id, func.count(Rule.id)).where(Rule.user_id == user_id, Rule.group_id.isnot(None)).group_by(Rule.group_id)
        )).all()
        count_map = {str(gid): cnt for gid, cnt in rule_counts}
        return {"items": [
            {"id": str(g.id), "name": g.name, "parent_id": str(g.parent_id) if g.parent_id else None,
             "sort_order": g.sort_order, "rule_count": count_map.get(str(g.id), 0)}
            for g in groups
        ]}


@router.post("/rule-groups")
async def create_rule_group(request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        from app.tools.skill_router.db.models import RuleGroup
        user_id = await _user_id(user, db=db)
        name = data.get("name", "").strip()
        parent_id = uuid.UUID(data["parent_id"]) if data.get("parent_id") else None
        # Check name uniqueness
        existing = await db.execute(select(RuleGroup).where(
            RuleGroup.user_id == user_id, RuleGroup.name == name, RuleGroup.parent_id == parent_id
        ))
        if existing.scalar_one_or_none():
            return JSONResponse({"error": "Group name already exists"}, status_code=400)
        g = RuleGroup(user_id=user_id, name=name, parent_id=parent_id, sort_order=data.get("sort_order", 0))
        db.add(g)
        await db.commit()
        await db.refresh(g)
    return {"ok": True, "id": str(g.id)}


@router.patch("/rule-groups/{group_id}")
async def update_rule_group(group_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    async with get_session() as db:
        from app.tools.skill_router.db.models import RuleGroup
        user_id = await _user_id(user, db=db)
        g = await db.get(RuleGroup, uuid.UUID(group_id))
        if not g or g.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=404)
        if "name" in data: g.name = data["name"].strip()
        if "parent_id" in data: g.parent_id = uuid.UUID(data["parent_id"]) if data["parent_id"] else None
        if "sort_order" in data: g.sort_order = data["sort_order"]
        await db.commit()
    return {"ok": True}


@router.delete("/rule-groups/{group_id}")
async def delete_rule_group(group_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with get_session() as db:
        from app.tools.skill_router.db.models import RuleGroup, Rule
        user_id = await _user_id(user, db=db)
        g = await db.get(RuleGroup, uuid.UUID(group_id))
        if not g or g.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=404)
        # check for children
        children = (await db.execute(select(RuleGroup).where(RuleGroup.parent_id == g.id))).scalars().all()
        if children:
            return JSONResponse({"error": "Group has children, delete them first"}, status_code=400)
        # ungroup rules in this group
        rules = (await db.execute(select(Rule).where(Rule.group_id == g.id))).scalars().all()
        for rule in rules:
            rule.group_id = None
        await db.delete(g)
        await db.commit()
    return {"ok": True}


@router.post("/rules/{rule_id}/move")
async def move_rule_to_group(rule_id: str, request: Request):
    user = _check_auth(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    group_id = data.get("group_id")
    async with get_session() as db:
        from app.tools.skill_router.db.models import Rule, RuleGroup
        user_id = await _user_id(user, db=db)
        rule = await db.get(Rule, uuid.UUID(rule_id))
        if not rule or rule.user_id != user_id:
            return JSONResponse({"error": "not found"}, status_code=404)
        if group_id:
            g = await db.get(RuleGroup, uuid.UUID(group_id))
            if not g or g.user_id != user_id:
                return JSONResponse({"error": "group not found"}, status_code=404)
            rule.group_id = uuid.UUID(group_id)
        else:
            rule.group_id = None
        await db.commit()
    return {"ok": True}


# ------ Skill Import ------

@router.post("/skills/import/preview")
async def import_preview(request: Request):
    """Preview a skill from GitHub or ClawHub URL before importing."""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    data = await request.json()
    url = data.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)

    from app.tools.skill_router.services.import_service import ImportService
    try:
        source = ImportService.detect_source(url)
        if source == "clawhub":
            result = await ImportService.import_from_clawhub(url)
        else:
            result = await ImportService.import_from_github(url)
        return result
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"Failed to fetch skill: {str(e)}"}, status_code=500)


@router.post("/skills/import/search")
async def import_search(request: Request):
    """Search GitHub for skills."""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    data = await request.json()
    query = data.get("query", "").strip()
    source = data.get("source", "github")

    if not query:
        return JSONResponse({"error": "query required"}, status_code=400)

    from app.tools.skill_router.services.import_service import ImportService
    try:
        if source == "clawhub":
            results = await ImportService.search_clawhub(query)
        else:
            results = await ImportService.search_github_repos(query)
        return {"results": results}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/skills/import")
async def import_skill(request: Request):
    """Import a skill from GitHub."""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    data = await request.json()
    url = data.get("url", "").strip()
    group_id = data.get("group_id")

    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)

    from app.tools.skill_router.services.import_service import ImportService
    from app.tools.skill_router.db.models import SkillGroup

    try:
        source = ImportService.detect_source(url)
        if source == "clawhub":
            result = await ImportService.import_from_clawhub(url)
        else:
            result = await ImportService.import_from_github(url)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Failed to import: {type(e).__name__}: {str(e)}"}, status_code=500)

    if "available_skills" in result:
        return JSONResponse({"error": "Multiple skills found. Please specify a path.", "available": result["available_skills"]}, status_code=400)

    try:
        async with get_session() as db:
            user_id = await _user_id(user, db=db)

            # Validate group
            gid = None
            if group_id:
                g = await db.get(SkillGroup, uuid.UUID(group_id))
                if g and g.user_id == user_id:
                    gid = uuid.UUID(group_id)

            skill = Skill(
                name=result["name"],
                description=result.get("description", ""),
                content=result["content"],
                user_id=user_id,
                group_id=gid,
                source_url=result.get("source_url"),
                source_type=result.get("source_type"),
                source_id=result.get("source_id"),
            )
            db.add(skill)
            await db.flush()

            # Add files
            for i, f in enumerate(result.get("files", [])):
                db.add(SkillFile(
                    skill_id=skill.id,
                    path=f["path"],
                    content=f["content"],
                    is_entry=f.get("is_entry", False),
                    sort_order=i,
                ))

            await db.commit()
            await db.refresh(skill)

            return {"ok": True, "skill_id": str(skill.id), "name": skill.name}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Database error: {type(e).__name__}: {str(e)}"}, status_code=500)
