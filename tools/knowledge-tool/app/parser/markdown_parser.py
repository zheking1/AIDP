import hashlib
import re
from typing import Optional

from app.parser.base import ParseInput, ParsedDocument, ParsedSection


class MarkdownParser:
    """Parse Markdown documents into sections based on headings."""

    def supports(self, input: ParseInput) -> bool:
        if input.mime_type and input.mime_type in ("text/markdown", "text/x-markdown"):
            return True
        if input.file_name and input.file_name.endswith((".md", ".markdown")):
            return True
        if input.content is not None:
            return True
        return False

    def parse(self, input: ParseInput) -> ParsedDocument:
        content = input.content or ""
        if input.file_path:
            with open(input.file_path, "r", encoding="utf-8") as f:
                content = f.read()

        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        title = self._extract_title(content, input.file_name)
        sections = self._split_into_sections(content)

        return ParsedDocument(
            title=title,
            sections=sections,
            checksum=checksum,
        )

    def _extract_title(self, content: str, file_name: Optional[str] = None) -> str:
        for line in content.split("\n"):
            match = re.match(r"^#\s+(.+)$", line.strip())
            if match:
                return match.group(1).strip()
        if file_name:
            return file_name.rsplit(".", 1)[0]
        return "Untitled"

    def _split_into_sections(self, content: str) -> list[ParsedSection]:
        sections = []
        lines = content.split("\n")
        current_heading_path = []
        current_text_lines = []
        current_start_line = 1

        for i, line in enumerate(lines, 1):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                if current_text_lines:
                    text = "\n".join(current_text_lines).strip()
                    if text:
                        sections.append(ParsedSection(
                            heading_path=list(current_heading_path),
                            text=text,
                            start_line=current_start_line,
                            end_line=i - 1,
                        ))
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                current_heading_path = current_heading_path[:level - 1] + [heading_text]
                current_text_lines = []
                current_start_line = i
            else:
                current_text_lines.append(line)

        if current_text_lines:
            text = "\n".join(current_text_lines).strip()
            if text:
                sections.append(ParsedSection(
                    heading_path=list(current_heading_path),
                    text=text,
                    start_line=current_start_line,
                    end_line=len(lines),
                ))

        if not sections and content.strip():
            sections.append(ParsedSection(
                heading_path=[],
                text=content.strip(),
                start_line=1,
                end_line=len(lines),
            ))

        return sections
