import re
import markdown
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


class DocParser:
    def parse_markdown(self, content: str, url: str = "") -> Dict:
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(html, 'lxml')

        title = ""
        headings = soup.find_all(['h1', 'h2', 'h3'])
        if headings:
            title = headings[0].get_text(strip=True)

        sections = []
        for h in headings:
            section = {
                "heading": h.get_text(strip=True),
                "level": int(h.name[1]),
                "content": self._get_section_content(h),
            }
            sections.append(section)

        summary = content[:500] if len(content) > 500 else content
        return {
            "title": title,
            "url": url,
            "sections": sections,
            "summary": summary,
            "word_count": len(content.split()),
        }

    def parse_html(self, content: str, url: str = "") -> Dict:
        soup = BeautifulSoup(content, 'lxml')
        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(separator='\n', strip=True)
        summary = text[:500]
        return {
            "title": title,
            "url": url,
            "sections": [],
            "summary": summary,
            "word_count": len(text.split()),
        }

    def _get_section_content(self, heading) -> str:
        parts = []
        sibling = heading.find_next_sibling()
        while sibling:
            if sibling.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                break
            if sibling.name == 'p' or sibling.name == 'div':
                parts.append(sibling.get_text(strip=True))
            sibling = sibling.find_next_sibling()
        return '\n'.join(parts)[:1000]
