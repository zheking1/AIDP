import os
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

NAS_PROJECTS_ROOT = "/home/docker/AI-Code/projects"
NAS_SHARED_ROOT = "/home/docker/AI-Code/shared"


class NASStorageService:
    def __init__(self):
        self.projects_root = NAS_PROJECTS_ROOT
        self.shared_root = NAS_SHARED_ROOT

    def get_project_path(self, project_id: int) -> str:
        return os.path.join(self.projects_root, f"project-{project_id}")

    def project_exists(self, project_id: int) -> bool:
        path = self.get_project_path(project_id)
        return os.path.exists(path)

    def create_project_directory(self, project_id: int) -> str:
        path = self.get_project_path(project_id)
        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        os.makedirs(os.path.join(path, "docs"), exist_ok=True)
        os.makedirs(os.path.join(path, "tests"), exist_ok=True)
        os.makedirs(os.path.join(path, "configs"), exist_ok=True)
        return path

    def sync_code_from_git(self, project_id: int, source: str, branch: str = "main") -> str:
        path = self.get_project_path(project_id)
        if not os.path.exists(path):
            self.create_project_directory(project_id)
        try:
            if os.path.exists(os.path.join(path, ".git")):
                subprocess.run(
                    ["git", "-C", path, "pull", "origin", branch],
                    check=True,
                    capture_output=True
                )
            else:
                subprocess.run(
                    ["git", "clone", source, path],
                    check=True,
                    capture_output=True
                )
            return path
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"Git sync failed: {e.stderr.decode()}")

    def get_project_size(self, project_id: int) -> int:
        path = self.get_project_path(project_id)
        if not os.path.exists(path):
            return 0
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def list_project_files(self, project_id: int, path: str = "") -> list:
        project_path = self.get_project_path(project_id)
        target_path = os.path.join(project_path, path) if path else project_path
        if not os.path.exists(target_path):
            return []
        files = []
        for dirpath, dirnames, filenames in os.walk(target_path):
            for f in filenames:
                full_path = os.path.join(dirpath, f)
                rel_path = os.path.relpath(full_path, project_path)
                files.append(rel_path)
        return files[:100]

    def read_file(self, project_id: int, file_path: str) -> Optional[str]:
        project_path = self.get_project_path(project_id)
        full_path = os.path.join(project_path, file_path)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, project_id: int, file_path: str, content: str) -> bool:
        project_path = self.get_project_path(project_id)
        full_path = os.path.join(project_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def delete_project(self, project_id: int) -> bool:
        path = self.get_project_path(project_id)
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path)
            return True
        return False
