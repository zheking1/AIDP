from dataclasses import dataclass, field
from typing import Protocol, Optional


@dataclass
class ParsedSection:
    heading_path: list[str]
    text: str
    start_line: int
    end_line: int
    page_number: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    title: str
    sections: list[ParsedSection]
    metadata: dict = field(default_factory=dict)
    checksum: str = ""


@dataclass
class ParseInput:
    content: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: Optional[str] = None


class DocumentParser(Protocol):
    def supports(self, input: ParseInput) -> bool: ...
    def parse(self, input: ParseInput) -> ParsedDocument: ...
