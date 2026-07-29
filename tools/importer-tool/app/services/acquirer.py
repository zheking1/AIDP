import hashlib
import os
import re
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import settings


class AcquiredContent:
    def __init__(self, content: str, filename: Optional[str] = None,
                 source_uri: Optional[str] = None, mime_type: Optional[str] = None):
        self.content = content
        self.filename = filename
        self.source_uri = source_uri
        self.mime_type = mime_type
        self._checksum: Optional[str] = None

    @property
    def checksum(self) -> str:
        if self._checksum is None:
            self._checksum = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        return self._checksum

    def to_dict(self) -> dict:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "filename": self.filename,
            "source_uri": self.source_uri,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "size": len(self.content),
        }


class DirectoryEntry:
    def __init__(self, path: str, filename: str, size: int, ext: str):
        self.path = path
        self.filename = filename
        self.size = size
        self.ext = ext

    def to_dict(self) -> dict:
        return {"path": self.path, "filename": self.filename, "size": self.size, "ext": self.ext}


async def acquire_text(content: str, name: Optional[str] = None) -> AcquiredContent:
    if len(content) > settings.MAX_TEXT_LENGTH:
        content = content[:settings.MAX_TEXT_LENGTH]
    return AcquiredContent(content=content, filename=name, mime_type="text/plain")


async def acquire_url(url: str, name: Optional[str] = None) -> AcquiredContent:
    parsed = url.lower()
    if not parsed.startswith("http://") and not parsed.startswith("https://"):
        raise ValueError("Only http/https URLs are allowed")

    async with httpx.AsyncClient(timeout=settings.URL_TIMEOUT_SECONDS, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "AIDP-Importer/1.0"})
        resp.raise_for_status()
        body = resp.text

    soup = BeautifulSoup(body, "html.parser")
    title = name or (soup.title.string.strip() if soup.title else None) or "imported"
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)[:settings.URL_MAX_LENGTH]

    return AcquiredContent(
        content=text,
        filename=title,
        source_uri=url,
        mime_type="text/markdown",
    )


async def acquire_file(path: str) -> AcquiredContent:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not p.is_file():
        raise ValueError(f"Not a file: {path}")

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB")

    ext = p.suffix.lower()
    if ext not in settings.TEXT_EXTENSIONS and ext != "":
        raise ValueError(f"Unsupported file extension: {ext}")

    content = p.read_text(encoding="utf-8", errors="replace")
    return AcquiredContent(
        content=content,
        filename=p.name,
        source_uri=str(p.absolute()),
        mime_type=_guess_mime(ext),
    )


async def scan_directory(path: str, pattern: Optional[str] = None) -> list[DirectoryEntry]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not p.is_dir():
        raise ValueError(f"Not a directory: {path}")

    entries: list[DirectoryEntry] = []
    glob_pattern = pattern or "**/*"

    for file_path in p.glob(glob_pattern):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(p))
        parts = file_path.parts

        if any(ignore_dir in parts for ignore_dir in settings.IGNORE_DIRS):
            continue

        ext = file_path.suffix.lower()
        if ext not in settings.TEXT_EXTENSIONS:
            continue

        entries.append(DirectoryEntry(
            path=rel_path,
            filename=file_path.name,
            size=file_path.stat().st_size,
            ext=ext,
        ))

        if len(entries) >= settings.DIRECTORY_MAX_FILES:
            break

    entries.sort(key=lambda e: e.path)
    return entries


async def acquire_directory_file(base_path: str, rel_path: str) -> AcquiredContent:
    full_path = Path(base_path) / rel_path
    return await acquire_file(str(full_path))


def _guess_mime(ext: str) -> str:
    mapping = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".json": "application/json",
        ".xml": "text/xml",
        ".sql": "text/sql",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".ts": "text/typescript",
        ".sh": "text/x-shellscript",
        ".html": "text/html",
        ".css": "text/css",
        ".properties": "text/plain",
        ".env": "text/plain",
        ".cfg": "text/plain",
        ".ini": "text/plain",
        ".toml": "text/toml",
        ".csv": "text/csv",
    }
    return mapping.get(ext, "text/plain")
