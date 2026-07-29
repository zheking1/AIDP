"""Web import API for knowledge base - Direct import without conversation."""
import json
import logging
import re
import uuid
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.tools.knowledge_tool.tools.knowledge-tool.db.database import get_db
from app.tools.knowledge_tool.tools.knowledge-tool.db.models import KnowledgeBase, KtDocument
from app.tools.knowledge_tool.tools.knowledge-tool.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import-web", tags=["import-web"])


class DirectImportRequest(BaseModel):
    """Direct import request from URL."""
    url: HttpUrl
    kb_name: Optional[str] = None
    kb_level: str = "framework"  # framework, template, project
    auto_detect: bool = True


class WebImportService:
    """Service for importing web content into knowledge base."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def import_from_url(
        self, 
        db: AsyncSession,
        url: str, 
        kb_name: Optional[str] = None,
        kb_level: str = "framework",
        auto_detect: bool = True
    ) -> dict:
        """Import web content and create knowledge base."""
        
        # Step 1: Fetch content
        content = await self._fetch_page(url)
        if not content:
            raise ValueError("无法获取页面内容")
        
        # Step 2: Analyze content
        title = self._extract_title(content)
        description = self._extract_description(content)
        
        if auto_detect:
            tech_stack = self._detect_tech_stack(content)
            domains = self._extract_domains(content)
            kb_level = self._guess_kb_level(title, description, content)
        else:
            tech_stack = []
            domains = []
        
        # Step 3: Generate KB name
        final_kb_name = kb_name or self._generate_kb_name(title, url)
        
        # Step 4: Check if KB exists
        existing = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.name == final_kb_name)
        )
        if existing.scalar():
            # Append number to name
            final_kb_name = f"{final_kb_name}_{uuid.uuid4().hex[:4]}"
        
        # Step 5: Create knowledge base
        slug = final_kb_name.lower().replace(" ", "-").replace("_", "-")[:50]
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=final_kb_name,
            slug=slug,
            description=description or f"从 {url} 导入",
            kb_level=kb_level,
            domains=json.dumps(domains, ensure_ascii=False),
            keywords=json.dumps(tech_stack, ensure_ascii=False),
            tech_stack=json.dumps(tech_stack, ensure_ascii=False),
            visibility="public",
            chunk_size=512,
            overlap_size=50,
            embedding_model="text-embedding-3-small",
        )
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        
        # Step 6: Extract and create documents
        pages = self._extract_pages(content, url)
        doc_count = 0
        
        for i, page in enumerate(pages[:20]):  # Limit to 20 pages
            doc = KtDocument(
                id=str(uuid.uuid4()),
                knowledge_base_id=kb.id,
                title=page["title"][:200],
                content=page["content"],
                doc_type="web_page",
                source_url=page["url"],
                source_start_line=0,
                source_end_line=0,
                heading_path=json.dumps([], ensure_ascii=False),
                metadata_json=json.dumps({
                    "index": i,
                    "imported_from": url,
                    "auto_import": True,
                }, ensure_ascii=False),
            )
            db.add(doc)
            doc_count += 1
        
        await db.commit()
        
        return {
            "kb_id": kb.id,
            "kb_name": kb.name,
            "kb_level": kb.kb_level,
            "url": url,
            "document_count": doc_count,
            "tech_stack": tech_stack,
            "domains": domains,
        }
    
    async def _fetch_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch page content."""
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def _get_soup(self, html: str):
        """Lazy import BeautifulSoup."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, 'html.parser')
    
    def _extract_title(self, html: str) -> str:
        """Extract page title."""
        soup = self._get_soup(html)
        title = soup.find('title')
        if title:
            return title.get_text().strip()
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        return "Unknown"
    
    def _extract_description(self, html: str) -> str:
        """Extract page description."""
        soup = self._get_soup(html)
        meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta:
            return meta.get('content', '').strip()
        p = soup.find('p')
        if p:
            text = p.get_text().strip()
            return text[:200] + "..." if len(text) > 200 else text
        return ""
    
    def _detect_tech_stack(self, html: str) -> List[str]:
        """Detect technology keywords."""
        tech_keywords = [
            'java', 'python', 'javascript', 'typescript', 'go', 'rust',
            'spring', 'springboot', 'springcloud', 'spring boot', 'spring cloud',
            'react', 'vue', 'angular', 'django', 'flask', 'fastapi',
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'k8s', 'jenkins',
            'nacos', 'consul', 'eureka', 'zookeeper',
            'kafka', 'rabbitmq', 'rocketmq',
            'mybatis', 'jpa', 'hibernate',
            'oauth2', 'jwt', 'sso',
            'microservice', 'distributed', 'rpc', 'dubbo', 'grpc',
            'gateway', 'load balance', 'config', 'registry',
        ]
        
        soup = self._get_soup(html)
        text = soup.get_text().lower()
        
        found = []
        for tech in tech_keywords:
            if tech in text:
                found.append(tech)
        
        return found[:8]
    
    def _extract_domains(self, html: str) -> List[str]:
        """Extract domain tags."""
        domain_keywords = {
            'auth': ['authentication', 'oauth', 'jwt', 'sso', '登录', '认证'],
            'database': ['database', 'sql', 'mysql', 'postgres', 'redis', '数据库'],
            'messaging': ['kafka', 'rabbitmq', 'message', '消息'],
            'service-discovery': ['nacos', 'consul', 'eureka', 'registry', '注册中心'],
            'api-gateway': ['gateway', 'kong', 'apisix', '网关'],
            'monitoring': ['prometheus', 'grafana', '监控'],
            'deployment': ['docker', 'kubernetes', 'k8s', '部署'],
            'configuration': ['config', '配置中心'],
        }
        
        soup = self._get_soup(html)
        text = soup.get_text().lower()
        
        found = set()
        for domain, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in text:
                    found.add(domain)
                    break
        
        return list(found)[:5]
    
    def _guess_kb_level(self, title: str, description: str, html: str) -> str:
        """Guess knowledge base level."""
        text = (title + " " + description).lower()
        
        framework_indicators = ['framework', '基础', '通用', 'spring', 'runtime']
        for indicator in framework_indicators:
            if indicator in text:
                return "framework"
        
        template_indicators = ['template', '模板', '脚手架', 'starter']
        for indicator in template_indicators:
            if indicator in text:
                return "template"
        
        if 'docs' in text or 'documentation' in text:
            return "framework"
        
        return "template"
    
    def _generate_kb_name(self, title: str, url: str) -> str:
        """Generate KB name from title."""
        name = title.strip()
        
        # Remove common suffixes
        suffixes = ['- 官方文档', '- 文档', '- Documentation', '- Docs', 'Official', '|', '·']
        for suffix in suffixes:
            if suffix in name:
                name = name.split(suffix)[0].strip()
        
        # Use domain if title is generic
        if len(name) < 3 or name.lower() in ['home', 'index', '首页']:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            name = domain.split('.')[0].capitalize()
        
        return name[:40]
    
    def _extract_pages(self, html: str, url: str) -> List[dict]:
        """Extract content pages from HTML."""
        soup = self._get_soup(html)
        
        # Remove script/style/nav/footer
        for elem in soup(["script", "style", "nav", "footer"]):
            elem.decompose()
        
        pages = []
        title = self._extract_title(html)
        
        # Try to find main content
        main = soup.find('main') or soup.find('article') or soup.find('div', class_=['content', 'doc', 'documentation'])
        
        if main:
            # Split by headings
            sections = []
            current = {"title": title, "content": []}
            
            for elem in main.find_all(['h1', 'h2', 'h3', 'p', 'pre', 'li']):
                if elem.name in ['h1', 'h2', 'h3']:
                    if current["content"]:
                        sections.append(current)
                    current = {"title": elem.get_text().strip(), "content": []}
                else:
                    text = elem.get_text().strip()
                    if text and len(text) > 10:
                        current["content"].append(text)
            
            if current["content"]:
                sections.append(current)
            
            for i, sec in enumerate(sections[:15]):
                content = "\n\n".join(sec["content"])
                if len(content) > 50:
                    pages.append({
                        "title": sec["title"] or f"Section {i+1}",
                        "content": content[:4000],
                        "url": url,
                    })
        
        # Fallback: use whole page
        if not pages:
            text = soup.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            text = '\n'.join(lines)
            
            if len(text) > 100:
                pages.append({
                    "title": title,
                    "content": text[:8000],
                    "url": url,
                })
        
        return pages


# Global service instance
_import_service = WebImportService()


@router.post("/direct-import", response_model=ApiResponse)
async def direct_import(
    req: DirectImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Directly import web content into knowledge base."""
    try:
        result = await _import_service.import_from_url(
            db=db,
            url=str(req.url),
            kb_name=req.kb_name,
            kb_level=req.kb_level,
            auto_detect=req.auto_detect,
        )
        return ApiResponse(data=result, message="导入成功")
    except ValueError as e:
        return ApiResponse(success=False, message=str(e))
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return ApiResponse(success=False, message=f"导入失败: {str(e)}")


@router.post("/analyze", response_model=ApiResponse)
async def analyze_url_only(req: DirectImportRequest):
    """Only analyze URL without importing."""
    try:
        content = await _import_service._fetch_page(str(req.url))
        if not content:
            return ApiResponse(success=False, message="无法获取页面内容")
        
        title = _import_service._extract_title(content)
        description = _import_service._extract_description(content)
        tech_stack = _import_service._detect_tech_stack(content)
        domains = _import_service._extract_domains(content)
        kb_level = _import_service._guess_kb_level(title, description, content)
        suggested_name = req.kb_name or _import_service._generate_kb_name(title, str(req.url))
        
        return ApiResponse(data={
            "url": str(req.url),
            "title": title,
            "description": description,
            "suggested_name": suggested_name,
            "suggested_kb_level": kb_level,
            "tech_stack": tech_stack,
            "domains": domains,
        })
    except Exception as e:
        logger.error(f"Analyze failed: {e}")
        return ApiResponse(success=False, message=str(e))
