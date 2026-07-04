from dataclasses import dataclass
from typing import Protocol, BinaryIO, Optional


@dataclass
class StoragePutRequest:
    workspace_id: str
    project_id: Optional[str]
    document_id: str
    version: str
    file_name: str


@dataclass
class StoredObject:
    object_key: str
    size: int
    checksum: str


class ObjectStorage(Protocol):
    def put(self, data: BinaryIO, request: StoragePutRequest) -> StoredObject: ...
    def get(self, object_key: str) -> BinaryIO: ...
    def delete(self, object_key: str) -> None: ...
    def exists(self, object_key: str) -> bool: ...
