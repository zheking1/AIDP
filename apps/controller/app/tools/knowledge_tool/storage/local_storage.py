import hashlib
import os
from typing import BinaryIO, Optional

from app.tools.knowledge_tool.storage.base import StoragePutRequest, StoredObject


class LocalObjectStorage:
    """Local filesystem object storage for MVP."""

    def __init__(self, root_path: str = "./data/knowledge"):
        self._root_path = root_path
        os.makedirs(root_path, exist_ok=True)

    def put(self, data: BinaryIO, request: StoragePutRequest) -> StoredObject:
        project_id = request.project_id or "global"
        safe_file_name = request.file_name.replace("/", "_").replace("\\", "_")
        object_key = f"files/{request.workspace_id}/{project_id}/{request.document_id}/{request.version}/{safe_file_name}"

        full_path = os.path.join(self._root_path, object_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        content = data.read()
        with open(full_path, "wb") as f:
            f.write(content)

        checksum = hashlib.sha256(content).hexdigest()

        return StoredObject(
            object_key=object_key,
            size=len(content),
            checksum=checksum,
        )

    def get(self, object_key: str) -> BinaryIO:
        full_path = os.path.join(self._root_path, object_key)
        return open(full_path, "rb")

    def delete(self, object_key: str) -> None:
        full_path = os.path.join(self._root_path, object_key)
        if os.path.exists(full_path):
            os.remove(full_path)

    def exists(self, object_key: str) -> bool:
        full_path = os.path.join(self._root_path, object_key)
        return os.path.exists(full_path)
