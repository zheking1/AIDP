import re
import base64
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import httpx
import yaml


class ImportService:
    GITHUB_API = "https://api.github.com"
    CLAWHUB_API = "https://clawhub.ai/api/v1"

    # --- URL Detection ---

    @staticmethod
    def detect_source(url: str) -> str:
        """Detect URL source: github, clawhub, or unknown."""
        url = url.strip().lower()
        if "clawhub.ai" in url:
            return "clawhub"
        if "github.com" in url or "/" in url and not url.startswith("http"):
            return "github"
        return "unknown"

    # --- ClawHub Import ---

    @staticmethod
    async def import_from_clawhub(url: str) -> Dict[str, Any]:
        """Import a skill from ClawHub URL.
        
        ClawHub is a SPA - content loaded via JS, API is unreliable.
        Best effort: try to extract skill name and search GitHub.
        """
        # Parse URL: https://clawhub.ai/owner/skills/skill-name or similar
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        # Extract owner and skill name from URL
        owner = ""
        skill_name = ""
        if len(path_parts) >= 2:
            owner = path_parts[0]
            if "skills" in path_parts:
                skills_idx = path_parts.index("skills")
                if skills_idx + 1 < len(path_parts):
                    skill_name = path_parts[skills_idx + 1]
            else:
                skill_name = path_parts[-1]

        # Try to find on GitHub
        try:
            results = await ImportService.search_github_repos(f"{owner} {skill_name}", per_page=5)
            for r in results:
                if skill_name.lower() in r["name"].lower():
                    # Try to import from this GitHub repo
                    github_url = f"https://github.com/{r['full_name']}"
                    result = await ImportService.import_from_github(github_url)
                    result["source_url"] = url  # Keep original ClawHub URL
                    result["source_type"] = "clawhub"
                    result["source_id"] = f"clawhub/{owner}/{skill_name}"
                    return result
        except Exception:
            pass

        raise ValueError(
            f"ClawHub skills cannot be imported directly. "
            f"Please find the GitHub source URL for this skill and use that instead."
        )

    # --- GitHub URL Parsing ---

    @staticmethod
    def parse_github_url(url: str) -> Optional[Dict[str, str]]:
        """Parse GitHub URL into owner/repo/path components.
        
        Supports:
        - https://github.com/owner/repo
        - https://github.com/owner/repo/tree/main/skills/skill-name
        - https://github.com/owner/repo/blob/main/SKILL.md
        - owner/repo/skills/skill-name
        """
        url = url.strip().rstrip("/")

        # Simple owner/repo/path format
        if not url.startswith("http"):
            parts = url.split("/")
            if len(parts) >= 2:
                return {
                    "owner": parts[0],
                    "repo": parts[1],
                    "path": "/".join(parts[2:]) if len(parts) > 2 else "",
                    "branch": "main",
                }
            return None

        parsed = urlparse(url)
        if "github.com" not in parsed.hostname:
            return None

        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            return None

        owner = path_parts[0]
        repo = path_parts[1]
        branch = "main"
        path = ""

        if len(path_parts) > 2 and path_parts[2] in ("tree", "blob"):
            branch = path_parts[3] if len(path_parts) > 3 else "main"
            path = "/".join(path_parts[4:])

        return {"owner": owner, "repo": repo, "path": path, "branch": branch}

    # --- GitHub API ---

    @staticmethod
    async def github_request(url: str) -> Any:
        """Make a GitHub API request."""
        from app.tools.skill_router.config import settings
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if settings.github_token:
                headers["Authorization"] = f"token {settings.github_token}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    @classmethod
    async def get_github_file(cls, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """Get file content from GitHub using raw URL (no rate limit)."""
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(raw_url, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            # Fallback to API
            try:
                api_url = f"{cls.GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
                data = await cls.github_request(api_url)
                if data.get("encoding") == "base64":
                    return base64.b64decode(data["content"]).decode("utf-8")
            except Exception:
                pass
            return None

    @classmethod
    async def list_github_dir(cls, owner: str, repo: str, path: str, branch: str = "main") -> List[Dict]:
        """List directory contents on GitHub."""
        url = f"{cls.GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        return await cls.github_request(url)

    @classmethod
    async def search_github_repos(cls, query: str, per_page: int = 10) -> List[Dict]:
        """Search GitHub repos for skills."""
        url = f"{cls.GITHUB_API}/search/repositories?q={query}+skill+in:name,description&sort=stars&per_page={per_page}"
        data = await cls.github_request(url)
        return [
            {
                "name": item["name"],
                "full_name": item["full_name"],
                "description": item.get("description", ""),
                "stars": item["stargazers_count"],
                "url": item["html_url"],
                "default_branch": item["default_branch"],
            }
            for item in data.get("items", [])
        ]

    # --- SKILL.md Parsing ---

    @staticmethod
    def parse_skill_md(content: str) -> Dict[str, Any]:
        """Parse SKILL.md frontmatter and body."""
        result = {"name": "", "description": "", "body": content, "tags": []}

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1])
                    if meta:
                        result["name"] = meta.get("name", "")
                        result["description"] = meta.get("description", "")
                except Exception:
                    pass
                result["body"] = parts[2].strip()

        if not result["name"]:
            first_line = result["body"].split("\n")[0].strip("# ").strip()
            result["name"] = first_line[:100] if first_line else "untitled"

        return result

    # --- Import from GitHub URL ---

    @classmethod
    async def import_from_github(cls, url: str) -> Dict[str, Any]:
        """Import a skill from a GitHub URL.
        
        Returns dict with: name, description, content, files, source_url, source_type, source_id
        """
        parsed = cls.parse_github_url(url)
        if not parsed:
            raise ValueError("Invalid GitHub URL")

        owner, repo, path, branch = parsed["owner"], parsed["repo"], parsed["path"], parsed["branch"]

        # If no path specified, look for SKILL.md in root or skills/ directory
        if not path:
            # Try root SKILL.md
            try:
                content = await cls.get_github_file(owner, repo, "SKILL.md", branch)
                if content:
                    meta = cls.parse_skill_md(content)
                    files = [{"path": "SKILL.md", "content": content, "is_entry": True}]
                    return {
                        "name": meta["name"],
                        "description": meta["description"],
                        "content": meta["body"],
                        "files": files,
                        "source_url": f"https://github.com/{owner}/{repo}",
                        "source_type": "github",
                        "source_id": f"{owner}/{repo}",
                    }
            except Exception:
                pass

            # Try skills/ directory
            try:
                items = await cls.list_github_dir(owner, repo, "skills", branch)
                if items:
                    # Return list of available skills
                    skills = []
                    for item in items:
                        if item["type"] == "dir":
                            skills.append({
                                "name": item["name"],
                                "path": f"skills/{item['name']}",
                                "type": "directory",
                            })
                    return {"available_skills": skills, "source_url": f"https://github.com/{owner}/{repo}"}
            except Exception:
                pass

            raise ValueError(f"No SKILL.md found in {owner}/{repo}")

        # Path specified - import that specific skill
        # Ensure path ends with SKILL.md or find it
        if not path.endswith("SKILL.md"):
            # Check if SKILL.md exists in the path
            content = await cls.get_github_file(owner, repo, f"{path}/SKILL.md", branch)
            if content:
                path = f"{path}/SKILL.md"
            else:
                raise ValueError(f"No SKILL.md found at {path}")

        # Get the SKILL.md content
        content = await cls.get_github_file(owner, repo, path, branch)
        if not content:
            raise ValueError("Failed to fetch SKILL.md")

        meta = cls.parse_skill_md(content)
        files = [{"path": "SKILL.md", "content": content, "is_entry": True}]

        # Get the skill directory path (without SKILL.md)
        dir_path = path.replace("/SKILL.md", "").replace("SKILL.md", "")

        # Try to get supporting files (skip if rate limited)
        try:
            items = await cls.list_github_dir(owner, repo, dir_path, branch)
            for item in items:
                if item["type"] == "file" and item["name"] != "SKILL.md":
                    file_content = await cls.get_github_file(owner, repo, item["path"], branch)
                    if file_content:
                        files.append({
                            "path": item["name"],
                            "content": file_content,
                            "is_entry": False,
                        })
                elif item["type"] == "dir":
                    # Recursively get files from subdirectories
                    try:
                        sub_items = await cls.list_github_dir(owner, repo, item["path"], branch)
                        for sub_item in sub_items:
                            if sub_item["type"] == "file":
                                file_content = await cls.get_github_file(owner, repo, sub_item["path"], branch)
                                if file_content:
                                    rel_path = item["name"] + "/" + sub_item["name"]
                                    files.append({
                                        "path": rel_path,
                                        "content": file_content,
                                        "is_entry": False,
                                    })
                    except Exception:
                        pass
        except Exception:
            pass  # Skip supporting files if we can't list them

        return {
            "name": meta["name"],
            "description": meta["description"],
            "content": meta["body"],
            "files": files,
            "source_url": f"https://github.com/{owner}/{repo}/tree/{branch}/{dir_path}",
            "source_type": "github",
            "source_id": f"{owner}/{repo}/{dir_path}",
        }

    # --- ClawHub API ---

    @classmethod
    async def search_clawhub(cls, query: str) -> List[Dict]:
        """Search ClawHub for skills."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{cls.CLAWHUB_API}/skills/search", params={"q": query})
                resp.raise_for_status()
                data = resp.json()
                return [
                    {
                        "name": s.get("name", ""),
                        "slug": s.get("slug", ""),
                        "description": s.get("description", ""),
                        "downloads": s.get("downloads", 0),
                    }
                    for s in data.get("skills", [])
                ]
        except Exception:
            return []

    @classmethod
    async def get_clawhub_skill(cls, slug: str) -> Dict[str, Any]:
        """Get skill details from ClawHub."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{cls.CLAWHUB_API}/skills/{slug}")
            resp.raise_for_status()
            return resp.json()
