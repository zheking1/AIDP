#!/usr/bin/env python3
"""
Create test data for Memory Tool
Includes diverse memories with categories, relations, and context packages
"""
import asyncio
import json
import math
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

BASE_URL = "http://192.168.0.100:18085"

# Valid categories: architecture, decision, pattern, issue, bug, other
SAMPLE_MEMORIES = {
    "architecture": [
        {"title": "User Authentication System", "content": "Implement JWT token authentication with refresh token support. Access token expires in 15 minutes, refresh token valid for 7 days.", "tags": ["auth", "jwt", "security"]},
        {"title": "Database Design Pattern", "content": "Use PostgreSQL with SQLAlchemy ORM. Implement repository pattern for data access layer abstraction.", "tags": ["database", "postgresql", "sqlalchemy"]},
        {"title": "API Gateway Architecture", "content": "RESTful API design with FastAPI. Auto-generated OpenAPI docs, Pydantic validation, async endpoints.", "tags": ["api", "rest", "fastapi"]},
        {"title": "Frontend Architecture", "content": "Alpine.js + TailwindCSS for lightweight reactive UI. Component-based structure with event-driven updates.", "tags": ["frontend", "alpine", "tailwind"]},
        {"title": "Caching Strategy", "content": "Multi-tier caching: L1 in-memory, L2 Redis. Cache invalidation via pub/sub pattern.", "tags": ["cache", "redis", "performance"]},
    ],
    "bug": [
        {"title": "Memory Leak in D3.js Charts", "content": "SVG elements not properly disposed on re-render. Fix: call svg.remove() and nullify references.", "tags": ["d3", "memory", "fix"]},
        {"title": "Database Connection Pool Exhaustion", "content": "Concurrent requests deplete connection pool. Solution: increase pool size and add connection timeout.", "tags": ["concurrency", "database", "fix"]},
        {"title": "Unicode Encoding Issue", "content": "Chinese characters display as garbled text in some browsers. Fix: enforce UTF-8 encoding in all layers.", "tags": ["encoding", "utf8", "i18n"]},
    ],
    "decision": [
        {"title": "Backend Framework Choice", "content": "Selected FastAPI over Flask. Rationale: native async support, automatic API docs, type hints.", "tags": ["decision", "fastapi", "architecture"]},
        {"title": "Deployment Strategy", "content": "Docker Compose on NAS for easy backup and migration. Traefik reverse proxy for SSL termination.", "tags": ["decision", "docker", "deployment"]},
        {"title": "Database Selection", "content": "PostgreSQL as primary, SQLite as fallback. Abstract repository layer for seamless switching.", "tags": ["decision", "database", "postgresql"]},
    ],
    "pattern": [
        {"title": "Vector Search with HNSW", "content": "HNSW index for approximate nearest neighbor search. O(log n) complexity, suitable for high-dimensional vectors.", "tags": ["vector", "hnsw", "algorithm"]},
        {"title": "Token Estimation Algorithm", "content": "OpenAI token estimation: Chinese chars x 2, English chars / 4. Provides ~90% accuracy.", "tags": ["token", "openai", "llm"]},
        {"title": "Force-Directed Graph Layout", "content": "D3.js force simulation: charge force repels nodes, link force attracts connected nodes. Auto-stabilizes.", "tags": ["graph", "d3", "visualization"]},
        {"title": "Context Packaging Strategy", "content": "Build LLM context with priority ranking and token budget. Include summaries when exceeding limit.", "tags": ["context", "llm", "strategy"]},
    ],
    "issue": [
        {"title": "Python Async Pattern", "content": "Code snippet: async def fetch_data(): async with httpx.AsyncClient() as client: return await client.get(url)", "tags": ["python", "async", "snippet"]},
        {"title": "SQLAlchemy Relationship", "content": "Self-referential relationship: parent = relationship('MemoryEntry', remote_side='MemoryEntry.id', backref='children')", "tags": ["sqlalchemy", "relationship", "snippet"]},
        {"title": "D3.js Zoom Implementation", "content": "const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', e => g.attr('transform', e.transform))", "tags": ["d3", "zoom", "snippet"]},
    ],
    "other": [
        {"title": "Development Environment Setup", "content": "VS Code with Python extension, Black formatter, Pylance for type checking. Docker Desktop for local testing.", "tags": ["devtools", "vscode", "setup"]},
        {"title": "Code Review Checklist", "content": "1. Type hints present 2. Docstrings for public methods 3. Error handling 4. Unit tests 5. No hardcoded secrets", "tags": ["process", "review", "quality"]},
    ],
}

# Sample context packages
SAMPLE_CONTEXTS = [
    {
        "name": "Project Architecture Overview",
        "description": "Core knowledge about backend stack, database design, and API patterns",
        "memory_ids": [],
        "format": "markdown",
        "max_tokens": 2000,
    },
    {
        "name": "Frontend Development Guide",
        "description": "Frontend framework choices, UI components, interaction design patterns",
        "memory_ids": [],
        "format": "markdown",
        "max_tokens": 1500,
    },
    {
        "name": "Troubleshooting Handbook",
        "description": "Common bugs, performance issues, and solution summaries",
        "memory_ids": [],
        "format": "markdown",
        "max_tokens": 1000,
    },
]


async def create_memories(client: httpx.AsyncClient) -> List[dict]:
    """Create sample memories"""
    created_memories = []
    
    for category, memories in SAMPLE_MEMORIES.items():
        for mem in memories:
            # Generate embedding (384 dim with random values for testing)
            embedding = [random.uniform(-1, 1) for _ in range(384)]
            # Normalize to unit vector
            norm = math.sqrt(sum(x**2 for x in embedding))
            embedding = [x / norm for x in embedding]
            
            data = {
                "title": mem["title"],
                "content": mem["content"],
                "category": category,
                "tags": mem["tags"],
                "embedding": embedding,
                "ai_suggested": random.random() < 0.3,  # 30% are AI suggested
            }
            
            try:
                resp = await client.post(f"{BASE_URL}/api/memories", json=data)
                if resp.status_code in (200, 201):
                    result = resp.json()
                    created = result.get("data", result)
                    created_memories.append(created)
                    print(f"[OK] Created: {mem['title']} ({category})")
                else:
                    print(f"[ERR] Failed: {mem['title']} - {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"[ERR] Error: {mem['title']} - {e}")
    
    return created_memories


async def create_relations(client: httpx.AsyncClient, memories: List[dict]):
    """Create relations between memories"""
    # Group by category
    by_category = {}
    for mem in memories:
        cat = mem.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mem)
    
    # Create relations within same category
    relations_created = 0
    for cat, mems in by_category.items():
        if len(mems) >= 2:
            for i in range(len(mems) - 1):
                source = mems[i]
                target = mems[i + 1]
                
                relation_data = {
                    "source_id": source["id"],
                    "target_id": target["id"],
                    "relation_type": "related",
                    "strength": round(random.uniform(0.5, 1.0), 2),
                }
                
                try:
                    resp = await client.post(f"{BASE_URL}/api/relations", json=relation_data)
                    if resp.status_code in (200, 201):
                        relations_created += 1
                        print(f"[OK] Relation: {source['title'][:30]}... -> {target['title'][:30]}...")
                except Exception as e:
                    print(f"[ERR] Relation error: {e}")
    
    # Create some cross-category relations
    categories = list(by_category.keys())
    for i in range(min(5, len(categories))):
        cat1, cat2 = random.sample(categories, 2)
        if by_category[cat1] and by_category[cat2]:
            source = random.choice(by_category[cat1])
            target = random.choice(by_category[cat2])
            
            relation_data = {
                "source_id": source["id"],
                "target_id": target["id"],
                "relation_type": "depends_on",
                "strength": round(random.uniform(0.3, 0.8), 2),
            }
            
            try:
                resp = await client.post(f"{BASE_URL}/api/relations", json=relation_data)
                if resp.status_code in (200, 201):
                    relations_created += 1
                    print(f"[OK] Cross-relation: {source['title'][:20]}... -> {target['title'][:20]}...")
            except Exception as e:
                pass
    
    print(f"\nTotal relations created: {relations_created}")


async def create_context_packages(client: httpx.AsyncClient, memories: List[dict]):
    """Create sample context packages"""
    # Group memories by category for context selection
    by_category = {}
    for mem in memories:
        cat = mem.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mem["id"])
    
    contexts_to_create = [
        ("Project Architecture Overview", ["pattern", "decision", "architecture"]),
        ("Frontend Development Guide", ["architecture", "issue"]),
        ("Troubleshooting Handbook", ["bug", "pattern"]),
    ]
    
    for ctx_name, categories in contexts_to_create:
        memory_ids = []
        for cat in categories:
            if cat in by_category:
                # Take up to 3 memories from each category
                memory_ids.extend(by_category[cat][:3])
        
        if len(memory_ids) < 2:
            continue
        
        data = {
            "name": ctx_name,
            "description": f"Context package with {len(memory_ids)} related memories",
            "memory_ids": memory_ids[:8],  # Max 8 memories
            "format": "markdown",
            "max_tokens": random.choice([1000, 1500, 2000]),
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/api/context-packages", json=data)
            if resp.status_code in (200, 201):
                result = resp.json()
                created = result.get("data", result)
                print(f"[OK] Context package: {ctx_name} ({len(memory_ids)} memories, {created.get('actual_tokens', 0)} tokens)")
            else:
                print(f"[ERR] Failed context: {ctx_name} - {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Error context: {ctx_name} - {e}")


async def main():
    """Main function to create all test data"""
    print("=" * 60)
    print("Memory Tool Test Data Generator")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print("[ERR] Memory tool not responding")
                return
            print("[OK] Memory tool is healthy")
        except Exception as e:
            print(f"[ERR] Cannot connect to memory tool: {e}")
            return
        
        print("\n" + "-" * 40)
        print("Creating memories...")
        print("-" * 40)
        memories = await create_memories(client)
        
        if not memories:
            print("No memories created, stopping.")
            return
        
        print(f"\nTotal memories created: {len(memories)}")
        
        print("\n" + "-" * 40)
        print("Creating relations...")
        print("-" * 40)
        await create_relations(client, memories)
        
        print("\n" + "-" * 40)
        print("Creating context packages...")
        print("-" * 40)
        await create_context_packages(client, memories)
        
        print("\n" + "=" * 60)
        print("Test data creation complete!")
        print("=" * 60)
        print(f"\nAccess the web UI at:")
        print(f"  - Memories: {BASE_URL}/memories")
        print(f"  - Graph: {BASE_URL}/memories/graph")
        print(f"  - Context: {BASE_URL}/context")


if __name__ == "__main__":
    asyncio.run(main())
