from app.tools.knowledge_tool.chunk.base import ChunkCandidate, ChunkingOptions
from app.tools.knowledge_tool.parser.base import ParsedSection


class MarkdownChunker:
    """Chunk documents based on markdown headings and size limits."""

    def split(self, sections: list[ParsedSection], options: ChunkingOptions) -> list[ChunkCandidate]:
        chunks = []
        chunk_index = 0

        for section in sections:
            text = section.text
            if not text.strip():
                continue

            words = text.split()
            if len(words) <= options.chunk_size:
                chunks.append(ChunkCandidate(
                    content=text,
                    heading_path=section.heading_path,
                    start_line=section.start_line,
                    end_line=section.end_line,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1
            else:
                sub_chunks = self._split_large_section(text, options)
                for sub_text in sub_chunks:
                    chunks.append(ChunkCandidate(
                        content=sub_text,
                        heading_path=section.heading_path,
                        start_line=section.start_line,
                        end_line=section.end_line,
                        chunk_index=chunk_index,
                    ))
                    chunk_index += 1

        return chunks

    def _split_large_section(self, text: str, options: ChunkingOptions) -> list[str]:
        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = min(start + options.chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(chunk_text)

            if end >= len(words):
                break

            start = end - options.overlap

        return chunks
