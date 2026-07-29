"""
Web Import Service
网页导入服务 - 从 URL 抓取内容并导入知识库
"""
import httpx
from bs4 import BeautifulSoup
import re
import json
import hashlib
from datetime import datetime
from typing import Optional


TECH_KEYWORDS = {
    "java": "Java", "spring": "Spring", "springboot": "Spring Boot",
    "python": "Python", "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
    "javascript": "JavaScript", "typescript": "TypeScript", "node": "Node.js",
    "react": "React", "vue": "Vue.js", "angular": "Angular",
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "redis": "Redis", "mongodb": "MongoDB", "elasticsearch": "Elasticsearch",
    "rabbitmq": "RabbitMQ", "kafka": "Kafka", "nacos": "Nacos",
    "mybatis": "MyBatis", "jpa": "JPA", "hibernate": "Hibernate",
    "maven": "Maven", "gradle": "Gradle", "git": "Git",
    "linux": "Linux", "nginx": "Nginx", "tomcat": "Tomcat",
    "oauth2": "OAuth2", "jwt": "JWT", "graphql": "GraphQL",
    "grpc": "gRPC", "rest": "REST", "websocket": "WebSocket",
    "prometheus": "Prometheus", "grafana": "Grafana", "jenkins": "Jenkins",
    "swagger": "Swagger", "openapi": "OpenAPI", "sentinel": "Sentinel",
}

DOMAIN_KEYWORDS = {
    "auth": ["authentication", "authorization", "login", "oauth", "sso", "permission", "role", "user", "password"],
    "database": ["database", "sql", "nosql", "orm", "jpa", "mybatis", "redis", "cache", "persistence", "entity", "repository"],
    "messaging": ["message", "queue", "kafka", "rabbitmq", "event", "pub/sub", "notification", "websocket"],
    "api": ["api", "rest", "grpc", "endpoint", "controller", "route", "service", "microservice"],
    "config": ["configuration", "config", "nacos", "apollo", "env", "property", "yaml", "yml"],
    "monitoring": ["monitor", "metric", "alert", "prometheus", "grafana", "log", "tracing", "health"],
    "deployment": ["deploy", "docker", "kubernetes", "ci/cd", "jenkins", "pipeline", "release", "version"],
    "frontend": ["vue", "react", "angular", "html", "css", "javascript", "typescript", "ui", "component"],
}


class WebImportService:
    """网页导入服务"""

    def __init__(self):
        self.http = httpx.AsyncClient(
            timeout=30.0, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AIDP Knowledge Import/1.0)"}
        )

    async def analyze(self, url: str) -> dict:
        """分析 URL，返回页面信息（不导入）"""
        content, title, description = await self._fetch_and_parse(url)
        tech_stack = self._detect_tech_stack(content + title + description)
        domains = self._extract_domains(content)
        kb_level = self._guess_kb_level(content, title)
        kb_name = self._generate_kb_name(title, url)
        page_count = self._estimate_page_count(content)
        return {
            "url": url, "title": title, "description": description,
            "suggested_name": kb_name, "suggested_level": kb_level,
            "tech_stack": tech_stack, "domains": domains,
            "estimated_pages": page_count
        }

    async def import_from_url(self, url: str, kb_name: Optional[str] = None,
                             kb_level: str = "framework", auto_detect: bool = True) -> dict:
        """从 URL 导入内容到知识库"""
        from app.db.database import async_session_factory
        from app.modules.knowledge.models import KnowledgeBase, KnowledgeDocument
        from sqlalchemy import select

        content, title, description = await self._fetch_and_parse(url)

        if auto_detect:
            tech_stack = self._detect_tech_stack(content + title + description)
            domains = self._extract_domains(content)
            kb_level = self._guess_kb_level(content, title) or kb_level
        else:
            tech_stack = []
            domains = []

        final_name = kb_name or self._generate_kb_name(title, url)
        slug = self._slugify(final_name)

        async with async_session_factory() as db:
            existing = await db.execute(select(KnowledgeBase).where(KnowledgeBase.slug == slug))
            if existing.scalar_one_or_none():
                slug = slug + "-" + str(int(datetime.now().timestamp()))

            kb = KnowledgeBase(
                name=final_name, slug=slug,
                description=description[:500] if description else None,
                kb_level=kb_level,
                domains=json.dumps(domains), tech_stack=json.dumps(tech_stack),
                keywords=json.dumps(self._extract_keywords(content)),
                visibility="private"
            )
            db.add(kb)
            await db.flush()

            pages = self._extract_pages(content, title)
            for page in pages:
                doc = KnowledgeDocument(
                    base_id=kb.id, title=page["title"],
                    content=page["content"], source_type="web",
                    source_uri=url, category=kb_level,
                    processing_status="completed", index_status="indexed",
                    visibility="private", owner_type="system",
                    checksum=hashlib.md5(page["content"].encode()).hexdigest()
                )
                db.add(doc)
            await db.commit()
            await db.refresh(kb)

        return {
            "kb_id": kb.id, "kb_name": final_name,
            "kb_level": kb_level, "url": url,
            "document_count": len(pages),
            "tech_stack": tech_stack, "domains": domains
        }

    async def _fetch_and_parse(self, url: str) -> tuple:
        """抓取并解析页面"""
        resp = await self.http.get(url)
        resp.encoding = "utf-8"
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        description = self._extract_description(soup)

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        content = soup.get_text(separator="\n", strip=True)
        return content, title, description

    def _extract_title(self, soup: BeautifulSoup) -> str:
        t = soup.title.string if soup.title else None
        if not t:
            h1 = soup.find("h1")
            t = h1.get_text(strip=True) if h1 else ""
        return t.strip()[:200]

    def _extract_description(self, soup: BeautifulSoup) -> str:
        for meta in soup.find_all("meta"):
            if meta.get("name", "").lower() in ("description", "og:description"):
                return meta.get("content", "").strip()[:500]
        p = soup.find("p")
        return p.get_text(strip=True)[:500] if p else ""

    def _detect_tech_stack(self, text: str) -> list:
        lower = text.lower()
        found = set()
        for keyword, label in TECH_KEYWORDS.items():
            if keyword in lower:
                found.add(label)
        return sorted(found)[:10]

    def _extract_domains(self, text: str) -> list:
        lower = text.lower()
        found = set()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    found.add(domain)
                    break
        return sorted(found)

    def _extract_keywords(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', text)
        freq = {}
        for w in words:
            low = w.lower()
            if low not in ("the", "and", "for", "are", "not", "but", "you", "all", "can", "had", "her", "was", "one", "our", "out"):
                freq[low] = freq.get(low, 0) + 1
        return sorted(freq, key=freq.get, reverse=True)[:20]

    def _guess_kb_level(self, content: str, title: str) -> str:
        lower = (content + " " + title).lower()
        framework_indicators = ["framework", "tutorial", "guide", "documentation", "reference", "api reference", "getting started"]
        template_indicators = ["template", "starter", "boilerplate", "sample", "example", "demo"]
        project_indicators = ["project", "application", "system", "platform", "service", "microservice"]

        def score(indicators):
            return sum(1 for i in indicators if i in lower)

        scores = [
            ("framework", framework_indicators),
            ("template", template_indicators),
            ("project", project_indicators),
        ]
        best = max(scores, key=lambda x: score(x[1]))
        return best[0] if score(best[1]) > 0 else "framework"

    def _generate_kb_name(self, title: str, url: str) -> str:
        if title:
            name = re.sub(r'\s*[-|–—]\s*.*$', '', title).strip()[:100]
            if name:
                return name
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        parts = domain.split(".")
        return parts[-2].capitalize() if len(parts) >= 2 else domain[:100]

    def _estimate_page_count(self, content: str) -> int:
        headings = len(re.findall(r'^#{2,3}\s', content, re.MULTILINE))
        return max(1, min(headings, 50))

    def _extract_pages(self, content: str, title: str) -> list:
        """按标题拆分页面内容"""
        lines = content.split("\n")
        pages = []
        current_title = title or "概述"
        current_lines = []

        def flush():
            nonlocal current_title, current_lines
            text = "\n".join(current_lines).strip()
            if len(text) > 20:
                pages.append({"title": current_title[:200], "content": text})
            current_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# ") or stripped.startswith("## "):
                flush()
                current_title = stripped.lstrip("#").strip()
            else:
                current_lines.append(line)
        flush()
        return pages[:20]

    def _slugify(self, name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', s)
        return s.strip('-')[:120]