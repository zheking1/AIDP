#!/usr/bin/env python3
"""
lsjl-skill-cli — SkillRouter local skill manager.

Usage:
  srcli config set-server <url>
  srcli config set-api-key <key>
  srcli list [--q <query>] [--tag <tag>]
  srcli install <name|id>
  srcli run <name> [-- <params>...] [--pin <version>] [--no-auto-update] [--no-cleanup]
  srcli update [<name>]
  srcli diff <name>
  srcli rollback <name> <version>
  srcli info <name|id>
  srcli files <name|id>
  srcli push <path-to-tar-gz>
"""

import argparse
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library required. Install: pip install requests")
    sys.exit(1)

CACHE_DIR = Path.home() / ".skillcli"
CONFIG_FILE = CACHE_DIR / "config.json"
SKILLS_DIR = CACHE_DIR / "skills"


def _ensure_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def _load_config():
    _ensure_dirs()
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(cfg):
    _ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def _server():
    cfg = _load_config()
    url = cfg.get("server", "").rstrip("/")
    if not url:
        print("Error: server not configured. Run: srcli config set-server <url>")
        sys.exit(1)
    return url


def _headers():
    cfg = _load_config()
    h = {}
    if cfg.get("api_key"):
        h["X-API-Key"] = cfg["api_key"]
    return h


def _cache_path(name):
    return SKILLS_DIR / name


def _load_local_meta(name):
    path = _cache_path(name) / "meta.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_local_meta(name, meta):
    p = _cache_path(name)
    p.mkdir(parents=True, exist_ok=True)
    (p / "meta.json").write_text(json.dumps(meta, indent=2))


def _download_skill(name_or_id, version=None):
    url = f"{_server()}/api/skills/{name_or_id}/package"
    resp = requests.get(url, headers=_headers())
    if resp.status_code == 404:
        # Try search
        search = requests.get(f"{_server()}/api/skills/search?q={name_or_id}", headers=_headers())
        if search.status_code == 200:
            results = search.json()
            if results:
                url = f"{_server()}/api/skills/{results[0]['id']}/package"
                resp = requests.get(url, headers=_headers())
    if resp.status_code != 200:
        print(f"Error: skill '{name_or_id}' not found on server")
        sys.exit(1)
    
    skill_name = resp.headers.get("X-Skill-Name", name_or_id)
    buf = io.BytesIO(resp.content)
    files = []
    meta = {}

    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        meta_file = tar.extractfile("meta.json")
        if meta_file:
            meta = json.loads(meta_file.read())
        for m in tar.getmembers():
            if m.name.startswith("files/") and m.isfile():
                f = tar.extractfile(m)
                files.append({"path": m.name[len("files/"):], "content": f.read().decode() if f else ""})

    local_meta = {
        "id": meta.get("id", ""),
        "name": meta.get("name", skill_name),
        "version": version or meta.get("version", 1),
        "remote_version": meta.get("version", 1),
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "exec_config": meta.get("exec_config"),
        "review_status": meta.get("review_status", "pending"),
        "downloaded_at": time.time(),
        "files": files,
    }
    _save_local_meta(skill_name, local_meta)
    # Save files
    skill_dir = _cache_path(skill_name) / f"v{local_meta['version']}"
    skill_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        fp = skill_dir / f["path"]
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(f["content"])

    return local_meta


def _fetch_remote_meta(name_or_id):
    try:
        resp = requests.get(f"{_server()}/api/skills/{name_or_id}", headers=_headers(), timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ------ Commands ------

def cmd_config(args):
    cfg = _load_config()
    if args.config_key == "set-server":
        cfg["server"] = args.value
        _save_config(cfg)
        print(f"Server set to: {args.value}")
    elif args.config_key == "set-api-key":
        cfg["api_key"] = args.value
        _save_config(cfg)
        print("API key set")
    else:
        print(json.dumps(cfg, indent=2))


def cmd_list(args):
    params = {}
    if args.q:
        params["q"] = args.q
    if args.tag:
        params["tag"] = args.tag
    resp = requests.get(f"{_server()}/api/skills/search", params=params, headers=_headers())
    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}")
        return
    skills = resp.json()
    if not skills:
        print("No skills found")
        return
    print(f"{'Name':<25} {'Version':<8} {'Status':<10} {'Exec':<6} {'Tags'}")
    print("-" * 70)
    for s in skills:
        exec_mark = "✅" if s.get("executable") else " "
        tags = ", ".join(s.get("tags", [])[:3])
        print(f"{s['name']:<25} v{s['version']:<5} {s['review_status']:<10} {exec_mark:<6} {tags}")


def cmd_install(args):
    meta = _download_skill(args.name_or_id)
    print(f"Installed: {meta['name']} v{meta['version']}")
    if meta.get("exec_config") and meta["exec_config"].get("executable"):
        print(f"  Runtime: {meta['exec_config']['runtime']}")
        print(f"  Entry: {meta['exec_config']['entry']}")
        print(f"  Auto-update: {meta['exec_config'].get('auto_update', True)}")
    print(f"  Files: {len(meta.get('files', []))}")


def cmd_run(args):
    name = args.name
    local = _load_local_meta(name)

    if not local:
        print(f"Downloading '{name}'...")
        local = _download_skill(name)

    # Auto-update check
    auto = not getattr(args, "no_auto_update", False)
    if auto and local.get("exec_config", {}).get("auto_update", True):
        remote = _fetch_remote_meta(local.get("id", name))
        if remote and remote.get("version", 0) > local.get("remote_version", 0):
            print(f"Updating {name}: v{local['remote_version']} → v{remote['version']}")
            local = _download_skill(local.get("id", name), version=remote["version"])

    pin = getattr(args, "pin", None)
    version = pin or local.get("version", 1)
    exec_cfg = local.get("exec_config", {})
    if not exec_cfg or not exec_cfg.get("executable"):
        print(f"Error: '{name}' is not executable (no exec_config)")
        sys.exit(1)

    # Build params dict
    params = {}
    raw_params = getattr(args, "params", []) or []
    for p in raw_params:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.lstrip("-")] = v
        else:
            params[p.lstrip("-")] = "true"

    # Create temp workdir
    if getattr(args, "no_cleanup", not exec_cfg.get("cleanup", True)):
        workdir = _cache_path(name) / f"v{version}" / "_run"
        workdir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        workdir = Path(tempfile.mkdtemp(prefix=f"sr_{name}_"))
        cleanup = True

    # Copy files to workdir
    src_dir = _cache_path(name) / f"v{version}"
    if src_dir.exists():
        for item in src_dir.iterdir():
            if item.name != "_run":
                dst = workdir / item.name
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)

    # Render command
    cmd_template = exec_cfg.get("cmd_template", "")
    if not cmd_template:
        runtime = exec_cfg.get("runtime", "python3")
        entry = exec_cfg.get("entry", "main.py")
        cmd_template = f"{runtime} {{{{workdir}}}}/{entry}"

    cmd = cmd_template.replace("{workdir}", str(workdir)).replace("{entry}", exec_cfg.get("entry", ""))
    for k, v in params.items():
        cmd = cmd.replace(f"{{{k}}}", v)

    # Add remaining params as args (mapping=arg)
    mapping = exec_cfg.get("params", {}).get("mapping", "arg")
    if mapping == "arg":
        for k, v in params.items():
            if f"{{{k}}}" not in cmd_template:
                cmd += f" --{k} {shlex.quote(str(v))}"

    timeout = exec_cfg.get("timeout_secs", 60)
    print(f"▶ Running: {cmd}")
    print(f"  Workdir: {workdir}")
    print(f"  Timeout: {timeout}s")
    print("-" * 40)

    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            shell=True,
            timeout=timeout,
            capture_output=False,
        )
        if proc.returncode != 0:
            print(f"\n⚠ Exit code: {proc.returncode}")
    except subprocess.TimeoutExpired:
        print(f"\n✗ Timed out after {timeout}s")
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        if cleanup and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)


def cmd_update(args):
    name = args.name
    if name:
        local = _load_local_meta(name)
        if not local:
            print(f"'{name}' not installed locally. Use 'install' first.")
            return
        remote = _fetch_remote_meta(local.get("id", name))
        if not remote:
            print(f"Cannot reach server for '{name}'")
            return
        if remote.get("version", 0) > local.get("remote_version", 0):
            print(f"Updating {name}: v{local['remote_version']} → v{remote['version']}")
            _download_skill(local.get("id", name), version=remote["version"])
        else:
            print(f"{name} is up-to-date (v{local['remote_version']})")
    else:
        # Update all
        updated = 0
        for d in SKILLS_DIR.iterdir():
            if d.is_dir():
                local = _load_local_meta(d.name)
                if local:
                    remote = _fetch_remote_meta(local.get("id", d.name))
                    if remote and remote.get("version", 0) > local.get("remote_version", 0):
                        print(f"Updating {d.name}: v{local['remote_version']} → v{remote['version']}")
                        _download_skill(local.get("id", d.name), version=remote["version"])
                        updated += 1
        if updated == 0:
            print("All skills up-to-date")


def cmd_info(args):
    local = _load_local_meta(args.name_or_id)
    if not local:
        resp = requests.get(f"{_server()}/api/skills/{args.name_or_id}", headers=_headers())
        if resp.status_code != 200:
            print(f"Skill '{args.name_or_id}' not found")
            return
        info = resp.json()
    else:
        info = local

    print(f"Name:     {info.get('name', '')}")
    print(f"Version:  {info.get('remote_version', info.get('version', ''))}")
    print(f"Status:   {info.get('review_status', '')}")
    print(f"Tags:     {', '.join(info.get('tags', []) or [])}")
    print(f"Desc:     {info.get('description', '')}")
    exec_cfg = info.get("exec_config")
    if exec_cfg and exec_cfg.get("executable"):
        print(f"Runtime:  {exec_cfg.get('runtime', '')}")
        print(f"Entry:    {exec_cfg.get('entry', '')}")
        print(f"Auto-Upd: {exec_cfg.get('auto_update', True)}")


def cmd_diff(args):
    local = _load_local_meta(args.name)
    if not local:
        print(f"'{args.name}' not installed locally")
        return
    remote = _fetch_remote_meta(local.get("id", args.name))
    if not remote:
        print("Cannot reach server")
        return

    lv = local.get("remote_version", local.get("version", 0))
    rv = remote.get("version", 0)
    print(f"Local:  v{lv}")
    print(f"Remote: v{rv}")
    if rv > lv:
        print(f"\nNew version available: v{lv} → v{rv}")
        print("Run 'update' to upgrade")
    elif rv == lv:
        print("Up-to-date")
    else:
        print(f"Local is ahead (unusual)")


def cmd_rollback(args):
    local = _load_local_meta(args.name)
    if not local:
        print(f"'{args.name}' not installed")
        return
    target_version = args.version
    # Check if we have this version cached
    cached_dir = _cache_path(args.name) / f"v{target_version}"
    if not cached_dir.exists():
        resp = requests.get(f"{_server()}/api/skills/{local.get('id', args.name)}", headers=_headers())
        if resp.status_code != 200:
            print(f"Cannot fetch version info from server")
            return
        remote = resp.json()
        if remote.get("version") != int(target_version):
            print(f"Version v{target_version} not available locally or on server")
            return
        # Download specific version (current API always returns latest)
        local["version"] = int(target_version)
        _save_local_meta(args.name, local)
        print(f"Rolled back meta to v{target_version}")
    else:
        local["version"] = int(target_version)
        _save_local_meta(args.name, local)
        print(f"Rolled back to v{target_version}")


def cmd_files(args):
    local = _load_local_meta(args.name_or_id)
    if not local:
        resp = requests.get(f"{_server()}/api/skills/{args.name_or_id}/files", headers=_headers())
        if resp.status_code != 200:
            print(f"Skill '{args.name_or_id}' not found")
            return
        files = resp.json()
    else:
        files = local.get("files", [])

    if not files:
        print("No files")
        return
    for f in files:
        entry = " ▶" if f.get("is_entry") else "  "
        lang = f.get("language", "?")
        path = f.get("path", "?")
        size = len(f.get("content", ""))
        print(f" {entry} {lang:<8} {size:>6}B  {path}")


def cmd_push(args):
    path = args.path
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    with open(path, "rb") as f:
        resp = requests.post(
            f"{_server()}/api/skills/upload",
            data=f,
            headers={**_headers(), "Content-Type": "application/gzip"},
        )
    if resp.status_code == 200:
        result = resp.json()
        print(f"Uploaded: {result['name']} v{result['version']} (id: {result['id']})")
        print(f"  Files: {result.get('files', 0)}")
    else:
        print(f"Upload failed: {resp.status_code} {resp.text}")


def make_parser():
    p = argparse.ArgumentParser(prog="srcli", description="SkillRouter local skill manager")
    sub = p.add_subparsers(dest="command")

    # config
    cp = sub.add_parser("config", help="View or set config")
    cp.add_argument("config_key", nargs="?", default="", help="set-server or set-api-key")
    cp.add_argument("value", nargs="?", default="", help="value")
    cp.set_defaults(func=cmd_config)

    # list
    lp = sub.add_parser("list", help="Search skills on server")
    lp.add_argument("--q", help="Search query")
    lp.add_argument("--tag", help="Filter by tag")
    lp.set_defaults(func=cmd_list)

    # install
    ip = sub.add_parser("install", help="Download and cache a skill")
    ip.add_argument("name_or_id", help="Skill name or ID")
    ip.set_defaults(func=cmd_install)

    # run
    rp = sub.add_parser("run", help="Run a skill locally")
    rp.add_argument("name", help="Skill name")
    rp.add_argument("params", nargs="*", help="key=value parameters")
    rp.add_argument("--pin", help="Pin to specific version")
    rp.add_argument("--no-auto-update", action="store_true", help="Skip auto-update check")
    rp.add_argument("--no-cleanup", action="store_true", help="Keep workdir after execution")
    rp.set_defaults(func=cmd_run)

    # update
    up = sub.add_parser("update", help="Check for updates")
    up.add_argument("name", nargs="?", default=None, help="Skill name (omit for all)")
    up.set_defaults(func=cmd_update)

    # info
    inf = sub.add_parser("info", help="Show skill info")
    inf.add_argument("name_or_id", help="Skill name or ID")
    inf.set_defaults(func=cmd_info)

    # diff
    df = sub.add_parser("diff", help="Compare local vs server version")
    df.add_argument("name", help="Skill name")
    df.set_defaults(func=cmd_diff)

    # rollback
    rb = sub.add_parser("rollback", help="Rollback to a cached version")
    rb.add_argument("name", help="Skill name")
    rb.add_argument("version", help="Target version number")
    rb.set_defaults(func=cmd_rollback)

    # files
    ff = sub.add_parser("files", help="List files in a skill")
    ff.add_argument("name_or_id", help="Skill name or ID")
    ff.set_defaults(func=cmd_files)

    # push
    pp = sub.add_parser("push", help="Upload a skill package (.tar.gz)")
    pp.add_argument("path", help="Path to .tar.gz file")
    pp.set_defaults(func=cmd_push)

    return p


def main():
    p = make_parser()
    args = p.parse_args()
    if not args.command:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
