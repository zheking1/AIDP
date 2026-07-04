import hashlib
from dataclasses import dataclass, field
from typing import Protocol, Optional


@dataclass
class ChunkCandidate:
    content: str
    heading_path: list[str]
    start_line: int
    end_line: int
    chunk_index: int = 0
    content_hash: str = ""
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if not self.token_count:
            self.token_count = len(self.content.split())


@dataclass
class ChunkingOptions:
    chunk_size: int = 800
    overlap: int = 120
    max_chunk_size: int = 1600


class ChunkingStrategy(Protocol):
    def split(self, sections: list, options: ChunkingOptions) -> list[ChunkCandidate]: ...
