import os
import hashlib
import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime


class LLMClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "sk-xxx")
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")

    async def call(self, prompt: str, max_tokens: int = 2048) -> Optional[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception:
                return None

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts},
                )
                resp.raise_for_status()
                data = resp.json()
                return [item["embedding"] for item in data["data"]]
            except Exception:
                return []


class TwoStepIngestEngine:
    def __init__(self, db=None, llm_client: LLMClient = None):
        self.db = db
        self.llm = llm_client or LLMClient()

    async def ingest(self, title: str, content: str, workspace_id: str,
                     project_id: str = None, doc_type: str = "markdown") -> Dict:
        # Step 1: Analyze
        analysis = await self._analyze(content, title)

        # Step 2: Generate
        wiki_pages = await self._generate(title, content, analysis)

        # Save
        doc = await self._save_document(title, content, workspace_id, project_id, doc_type)

        return {
            "document_id": doc.get("id"),
            "analysis": analysis,
            "wiki_pages": wiki_pages,
        }

    async def _analyze(self, content: str, title: str) -> Dict:
        prompt = f"""Analyze this document and return JSON:

Title: {title}
Content: {content[:3000]}

Extract:
1. key_entities: list of class/function/concept names
2. core_concepts: list of main ideas
3. related_topics: topics this relates to
4. contradictions: potential conflicts with existing knowledge
5. suggested_tags: list of tags

Return JSON only:
{{"key_entities": [...], "core_concepts": [...], "related_topics": [...], "contradictions": [...], "suggested_tags": [...]}}
"""
        result = await self.llm.call(prompt, max_tokens=1024)
        if result:
            try:
                return json.loads(result)
            except:
                pass
        return {"key_entities": [], "core_concepts": [], "related_topics": [], "contradictions": [], "suggested_tags": []}

    async def _generate(self, title: str, content: str, analysis: Dict) -> List[Dict]:
        pages = []
        pages.append({
            "title": title,
            "type": "summary",
            "content": content[:2000],
            "frontmatter": {"tags": analysis.get("suggested_tags", [])},
        })
        for entity in analysis.get("key_entities", [])[:5]:
            pages.append({
                "title": f"{title} - {entity}",
                "type": "entity",
                "content": f"Entity: {entity}",
                "frontmatter": {},
            })
        return pages

    async def _save_document(self, title: str, content: str, workspace_id: str,
                             project_id: str = None, doc_type: str = "markdown") -> Dict:
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        return {
            "title": title,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "doc_type": doc_type,
            "checksum": checksum,
        }
