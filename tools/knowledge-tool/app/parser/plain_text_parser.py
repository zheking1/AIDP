import hashlib
from typing import Optional

from app.parser.base import ParseInput, ParsedDocument, ParsedSection


class PlainTextParser:
    """Parse plain text documents into sections."""

    def supports(self, input: ParseInput) -> bool:
        if input.mime_type and input.mime_type.startswith("text/"):
            return True
        if input.file_name and input.file_name.endswith((".txt", ".log", ".csv")):
            return True
        return False

    def parse(self, input: ParseInput) -> ParsedDocument:
        content = input.content or ""
        if input.file_path:
            with open(input.file_path, "r", encoding="utf-8") as f:
                content = f.read()

        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        title = input.file_name or "Untitled"
        if "." in title:
            title = title.rsplit(".", 1)[0]

        sections = self._split_into_sections(content)

        return ParsedDocument(
            title=title,
            sections=sections,
            checksum=checksum,
        )

    def _split_into_sections(self, content: str) -> list[ParsedSection]:
        sections = []
        paragraphs = content.split("\n\n")

        line_offset = 1
        for para in paragraphs:
            text = para.strip()
            if text:
                lines = text.split("\n")
                sections.append(ParsedSection(
                    heading_path=[],
                    text=text,
                    start_line=line_offset,
                    end_line=line_offset + len(lines) - 1,
                ))
                line_offset += len(lines) + 1
            else:
                line_offset += 1

        if not sections and content.strip():
            sections.append(ParsedSection(
                heading_path=[],
                text=content.strip(),
                start_line=1,
                end_line=content.count("\n") + 1,
            ))

        return sections
